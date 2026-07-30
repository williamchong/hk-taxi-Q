"""Download and cache a region's source datasets.

Two kinds of source, because publishers offer two shapes (see `config.py`):

* **Fixed URL** — roads, fares. Download once, keep.
* **Indexed** — buildings, delivered per map sheet. Fetch the publisher's sheet
  index, intersect it with the region bounds, download only the sheets that
  overlap. Which sheets those are is derived, never listed, so moving the region
  or adding a city re-derives the set for free.

Re-running is idempotent: an artefact already on disk at its recorded size is
left alone. That is deliberate rather than incidental — CLAUDE.md fixes the
snapshot, so upstream moving on must not silently change the map underfoot.

`--force` takes a new snapshot. It overrides fetch-once but not the publisher's
own version stamp, so unversioned sources re-download while versioned tiles are
pulled only where the revision actually moved.

Nothing here knows anything about any particular city.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from http.client import HTTPException
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from pipeline.config import CityConfig, RegionConfig, TiledSource, load_city
from pipeline.crs import GeodeticBounds, reproject_bounds

log = logging.getLogger(__name__)

SOURCES_ROOT = Path(__file__).resolve().parent.parent / "sources"
MANIFEST_NAME = "manifest.json"
INDEX_NAME = "index.geojson"

# Some government hosts reject the default `Python-urllib/3.x` agent outright,
# and the failure reads as a 403 rather than anything about the agent.
_USER_AGENT = "hk-taxi-Q-etl/0.1 (+build-time dataset fetch)"

_TIMEOUT_S = 60.0
_ATTEMPTS = 3
_RETRY_BACKOFF_S = 3.0
_CHUNK_BYTES = 1 << 20
_PROGRESS_INTERVAL_S = 5.0

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_NAME_SEPARATORS = frozenset({"/", "\\", "\0"})


class IncompleteResponseError(HTTPException):
    """A response ended before delivering its declared Content-Length.

    An `HTTPException` so it lands in `download`'s retry set alongside the other
    transport failures — a truncated transfer is exactly the kind that succeeds
    on a second attempt.
    """


class ArtefactKind(StrEnum):
    SOURCE = "source"
    # An index is metadata about what to download rather than payload, which is
    # why `--dry-run` fetches one and reports it apart from the rest.
    INDEX = "index"
    TILE = "tile"


@dataclass(frozen=True)
class Artefact:
    """One file to fetch, with the cache key that decides whether to skip it."""

    key: str
    url: str
    # Relative to `<root>/<city id>/` — resolve with `artefact_path`, never by
    # rebuilding that layout at the call site.
    path: Path
    # Publisher's version stamp. None means the artefact has no version and is
    # therefore fetched exactly once.
    version: str | None = None
    kind: ArtefactKind = ArtefactKind.SOURCE

    @property
    def tile_id(self) -> str:
        """The publisher's id for this tile — the sheet number, for buildings.

        A property because `key`'s `<source>/<id>` shape is this module's
        business; a caller splitting the string would be depending on it.
        """
        return self.key.rsplit("/", 1)[-1]


@dataclass
class FetchReport:
    downloaded: list[str]
    cached: list[str]
    # Indexes fetched this run. Tracked apart from `downloaded` because they are
    # fetched even under --dry-run, and reporting them as hypothetical would be
    # a lie about what touched the disk.
    indexes: list[str] = field(default_factory=list)
    total_bytes: int = 0

    @property
    def considered(self) -> int:
        return len(self.downloaded) + len(self.cached)


def redact(url: str) -> str:
    """Drop every part of a URL that can carry a credential.

    Applied to everything written to the manifest. `etl/sources/` is gitignored,
    so this is not the only thing standing between a key and the repo, but a
    credential that is never recorded cannot leak from a paste of a build log.

    The query string is where the publisher's API key lives, and `userinfo` is
    where basic-auth would live if a publisher ever used it — both go, because
    the contract here is "no credential is ever recorded", not "no key is".
    """
    parts = urlsplit(url)
    host = parts.hostname or ""
    if parts.port:
        host = f"{host}:{parts.port}"
    return parts._replace(netloc=host, query="", fragment="").geturl()


def _filename_for(url: str, fallback: str) -> str:
    """Filename for an artefact, constrained to one path segment.

    Both inputs can originate in a publisher's index, which is a remote document
    we do not control. Taking the basename already discards any directory part,
    so this mostly guards the leftovers — `..`, an empty segment, a stray
    separator — that would otherwise write outside the sources tree.

    `PurePosixPath`, not `Path`: a URL path is POSIX regardless of the host OS,
    and `Path` on Windows would treat a backslash as a separator and quietly
    accept a name this is meant to reject.
    """
    for candidate in (PurePosixPath(urlsplit(url).path).name, fallback):
        safe = _safe_segment(candidate)
        if safe is not None:
            return safe
    raise ValueError(f"cannot derive a safe filename from {redact(url)}")


def _safe_segment(candidate: str) -> str | None:
    """The candidate if it is usable as a single path component, else None."""
    if candidate and candidate not in {".", ".."} and not set(candidate) & _NAME_SEPARATORS:
        return candidate
    return None


def _check_scheme(url: str) -> None:
    """Refuse anything but HTTP(S).

    urllib will happily open `file://`, and these URLs are read out of a
    downloaded index rather than written by us.
    """
    scheme = urlsplit(url).scheme.lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"refusing to fetch {redact(url)}: scheme '{scheme}' is not http(s)")


# --------------------------------------------------------------------------
# Index handling
# --------------------------------------------------------------------------


def _positions(node: Any) -> Iterator[list[float]]:
    """Yield every coordinate pair in a GeoJSON geometry's nested arrays.

    Written structurally rather than per geometry type, so any nesting of
    coordinate arrays works — Point through MultiPolygon — without a change
    here. Not `GeometryCollection`, which nests under `geometries` rather than
    `coordinates`; a sheet index has no reason to use one.
    """
    if isinstance(node, list):
        if node and isinstance(node[0], (int, float)):
            yield node
        else:
            for child in node:
                yield from _positions(child)


def feature_bounds(geometry: Any) -> GeodeticBounds | None:
    """Envelope of a GeoJSON geometry, or None if it has no usable coordinates."""
    if not isinstance(geometry, dict):
        return None
    positions = list(_positions(geometry.get("coordinates")))
    if not positions:
        return None
    try:
        return GeodeticBounds.around([p[0] for p in positions], [p[1] for p in positions])
    except ValueError:
        # Degenerate footprint — a sheet with zero width or height is not a
        # sheet. Skip it rather than failing the whole run.
        return None


def select_tiles(
    index: dict[str, Any],
    source: TiledSource,
    *,
    region_bounds: GeodeticBounds,
    region_crs: str,
) -> list[Artefact]:
    """Tiles whose footprint overlaps the region, as artefacts ready to fetch.

    The region bounds are moved onto the index's datum first. Skipping that step
    is the failure this pipeline is most exposed to: the comparison still
    succeeds, just against the wrong rectangle, and selects a plausible set of
    neighbouring sheets.
    """
    target = reproject_bounds(region_bounds, from_crs=region_crs, to_crs=source.index_crs)

    selected: list[Artefact] = []
    for feature in index.get("features") or []:
        if not isinstance(feature, dict):
            continue
        bounds = feature_bounds(feature.get("geometry"))
        if bounds is None or not bounds.intersects(target):
            continue

        properties = feature.get("properties") or {}
        tile_id = _require_property(properties, source.id_property, source)
        url = _require_property(properties, source.url_property, source)
        version = (
            None
            if source.revision_property is None
            else _require_property(properties, source.revision_property, source)
        )
        selected.append(
            Artefact(
                key=f"{source.id}/{tile_id}",
                url=str(url),
                path=Path(source.id) / _tile_filename(str(tile_id), str(url), source),
                version=None if version is None else str(version),
                kind=ArtefactKind.TILE,
            )
        )

    # Stable order so logs and manifests diff cleanly between runs.
    return sorted(selected, key=lambda artefact: artefact.key)


def source_dir(city_id: str, source_id: str, *, root: Path | None = None) -> Path:
    """Where a source's fetched artefacts live."""
    return (root or SOURCES_ROOT) / city_id / source_id


def artefact_path(city_id: str, artefact: Artefact, *, root: Path | None = None) -> Path:
    """Where one fetched artefact lives.

    The single definition of the sources-tree layout. Later stages resolve
    through this rather than rebuilding `<root>/<city>/<path>` themselves, so
    moving the tree is one edit.
    """
    return (root or SOURCES_ROOT) / city_id / artefact.path


def source_artefact(source_id: str, url: str) -> Artefact:
    """One fixed-URL source as an artefact.

    The single definition of where a plain source lands on disk. `cached_source`
    resolves the same thing after the fact, and both go through here so a later
    stage cannot disagree with the fetcher about a filename.
    """
    return Artefact(key=source_id, url=url, path=Path(source_id) / _filename_for(url, source_id))


def cached_source(city: CityConfig, source_id: str, *, root: Path | None = None) -> Path:
    """Path to a fixed-URL source an earlier fetch left on disk.

    The counterpart of `cached_tiles` for the un-tiled half of `sources`, and it
    exists for the same reason: a stage that needs a fetched file should ask
    where it is rather than rebuild the path from a URL it re-derives itself.
    """
    if source_id not in city.sources:
        known = ", ".join(sorted(city.sources)) or "none"
        raise KeyError(f"city '{city.id}' has no source '{source_id}'. Known: {known}")

    artefact = source_artefact(source_id, city.sources[source_id])
    path = artefact_path(city.id, artefact, root=root)
    if not path.exists():
        raise FileNotFoundError(
            f"'{source_id}' has not been fetched to {path}. "
            f"Run: python -m pipeline.fetch --city {city.id} --region <region> --only {source_id}"
        )
    return path


def cached_tiles(
    city: CityConfig,
    region: RegionConfig,
    source: TiledSource,
    *,
    root: Path | None = None,
) -> list[Artefact]:
    """The region's tiles, selected from the index an earlier fetch left on disk.

    Exists so a later stage can discover which sheets it must read without
    either re-deriving the selection rule or hardcoding sheet numbers — the
    thing `P0-1` explicitly warned against. Offline: the index is already local.
    """
    index_path = source_dir(city.id, source.id, root=root) / INDEX_NAME
    if not index_path.exists():
        raise FileNotFoundError(
            f"no index for '{source.id}' at {index_path}. "
            f"Run: python -m pipeline.fetch --city {city.id} --region {region.id}"
        )
    index = read_feature_collection(index_path, f"tiled source {source.id!r} index")
    return select_tiles(index, source, region_bounds=region.bounds, region_crs=city.geodetic_crs)


def _tile_filename(tile_id: str, url: str, source: TiledSource) -> str:
    """Name a tile after its id, not after its URL's basename.

    The id is unique by construction; the basename is not. A publisher serving
    `/download?sheet=A` and `/download?sheet=B` would give both tiles the same
    filename, and they would overwrite each other on every run — silently, since
    each still records its own size and so each invalidates the other's cache
    entry forever. Assuming the query string is decorative is exactly the
    publisher-shape assumption this module exists to avoid.
    """
    suffix = PurePosixPath(urlsplit(url).path).suffix
    filename = _safe_segment(f"{tile_id}{suffix or '.bin'}")
    if filename is None:
        raise ValueError(
            f"tiled source '{source.id}': tile id {tile_id!r} is not usable as a filename"
        )
    return filename


def _require_property(properties: dict[str, Any], name: str, source: TiledSource) -> Any:
    """Read a configured property off a matched feature, loudly.

    Only matched features are validated. A publisher's index spans the whole
    territory and one malformed feature in a district we never visit should not
    stop the build; a malformed feature we actually need must.
    """
    if name not in properties:
        available = ", ".join(sorted(properties)) or "none"
        raise ValueError(
            f"tiled source '{source.id}': index feature has no property '{name}'. "
            f"Available: {available}"
        )
    return properties[name]


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_bytes())
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError):
        # A damaged manifest costs a re-download, not a crash. The artefacts
        # themselves are the real cache; this file only records what they are.
        log.warning("manifest at %s is unreadable — treating cache as empty", path)
        return {}


def _save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Written atomically, like the artefacts it indexes.

    A partial manifest is not a partial loss: `_load_manifest` cannot parse it,
    treats the cache as empty, and re-downloads everything. That is a bad
    outcome for one interrupted write of a small file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    partial.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(partial, path)


def _is_cached(entry: dict[str, Any] | None, path: Path, version: str | None) -> bool:
    if entry is None:
        return False
    try:
        size = path.stat().st_size
    except OSError:
        # Asked rather than pre-checked: `exists()` then `stat()` is two calls
        # that still race, and the second one raises anyway.
        return False
    if size != entry.get("size"):
        return False
    # A versioned artefact whose version moved is stale. An unversioned one is
    # fetch-once by definition.
    return version is None or entry.get("version") == version


# --------------------------------------------------------------------------
# Download
# --------------------------------------------------------------------------


def download(url: str, destination: Path) -> tuple[int, str]:
    """Stream a URL to disk atomically. Returns (bytes written, sha256).

    Writes to a sibling `.part` and renames on success, so neither an
    interrupted run nor a short response can leave a truncated file at the real
    path. `os.replace` is atomic within a filesystem.
    """
    _check_scheme(url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")

    last_error: Exception | None = None
    for attempt in range(1, _ATTEMPTS + 1):
        try:
            digest = hashlib.sha256()
            written = 0
            request = Request(url, headers={"User-Agent": _USER_AGENT})
            with urlopen(request, timeout=_TIMEOUT_S) as response, partial.open("wb") as handle:
                expected = _content_length(response)
                announced = time.monotonic()
                while chunk := response.read(_CHUNK_BYTES):
                    handle.write(chunk)
                    digest.update(chunk)
                    written += len(chunk)
                    if time.monotonic() - announced >= _PROGRESS_INTERVAL_S:
                        announced = time.monotonic()
                        log.info("    %s", _progress(written, expected))
            # `read(amt)` returns b'' on a premature close rather than raising —
            # CPython declines to raise IncompleteRead there for compatibility.
            # Without this check a server that drops mid-transfer yields a short
            # file that `os.replace` commits and the manifest then records at its
            # short size, making the truncation a permanent cache hit.
            if expected is not None and written != expected:
                raise IncompleteResponseError(
                    f"short read: {written} of {expected} bytes from {redact(url)}"
                )
            os.replace(partial, destination)
            return written, digest.hexdigest()
        except (HTTPError, URLError, TimeoutError, HTTPException, ConnectionError) as error:
            # Deliberately *not* bare OSError. Disk failures — ENOSPC above all,
            # very reachable at ~820 MB — are not transient, and retrying one
            # three times before reporting it as a download failure sends the
            # operator to look at the network.
            last_error = error
            partial.unlink(missing_ok=True)
            if attempt < _ATTEMPTS:
                # Restarting from zero rather than resuming with a Range header.
                # Simpler, and these are build-time fetches on a good link; add
                # resumption if a large source proves flaky in practice.
                log.warning("  attempt %d/%d failed (%s) — retrying", attempt, _ATTEMPTS, error)
                time.sleep(_RETRY_BACKOFF_S * attempt)
        except BaseException:
            # Includes KeyboardInterrupt: leaving a `.part` behind is harmless,
            # but leaving it behind is still worse than not.
            partial.unlink(missing_ok=True)
            raise

    raise RuntimeError(f"failed to download {redact(url)} after {_ATTEMPTS} attempts: {last_error}")


def _content_length(response: Any) -> int | None:
    raw = response.headers.get("Content-Length")
    return int(raw) if raw and raw.isdigit() else None


def _progress(written: int, expected: int | None) -> str:
    got = f"{written / 1e6:.1f} MB"
    if not expected:
        return f"{got} so far"
    return f"{got} of {expected / 1e6:.1f} MB ({100 * written / expected:.0f}%)"


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


def fetch_city(
    city: CityConfig,
    region_id: str,
    *,
    root: Path | None = None,
    force: bool = False,
    only: set[str] | None = None,
    dry_run: bool = False,
) -> FetchReport:
    """Fetch every source the region needs into `<root>/<city id>/`."""
    root = root or SOURCES_ROOT
    region = city.region(region_id)
    if only is not None:
        _check_source_names(city, only)
    manifest_path = root / MANIFEST_NAME
    manifest = _load_manifest(manifest_path)
    report = FetchReport(downloaded=[], cached=[])

    try:
        artefacts: list[Artefact] = [
            source_artefact(name, url)
            for name, url in sorted(city.sources.items())
            if only is None or name in only
        ]

        for source in city.tiled_sources.values():
            if only is not None and source.id not in only:
                continue
            artefacts.extend(_tiles_for(source, city, region, root, manifest, report, force=force))

        for artefact in artefacts:
            _process(artefact, city, root, manifest, report, force=force, dry_run=dry_run)
    finally:
        # In a `finally` because a failure partway through must not throw away
        # what already succeeded. Without this, one dropped connection on the
        # sixth 44 MB sheet costs all five that landed before it.
        _save_manifest(manifest_path, manifest)

    return report


def _tiles_for(
    source: TiledSource,
    city: CityConfig,
    region: RegionConfig,
    root: Path,
    manifest: dict[str, Any],
    report: FetchReport,
    *,
    force: bool,
) -> list[Artefact]:
    """Fetch a tiled source's index and turn it into the region's artefacts."""
    index_artefact = Artefact(
        key=f"{source.id}/index",
        url=source.index_url,
        path=Path(source.id) / INDEX_NAME,
        kind=ArtefactKind.INDEX,
    )
    # The index is fetched even under --dry-run, and it is the one thing that
    # is. Without it there are no tile names to report, so a dry run on a cold
    # cache could not answer the only question it is asked. It is small, and it
    # is metadata about the download rather than the payload.
    _process(index_artefact, city, root, manifest, report, force=force, dry_run=False)

    index_path = artefact_path(city.id, index_artefact, root=root)
    try:
        index = read_feature_collection(index_path, f"tiled source {source.id!r} index")
    except ValueError:
        # Evict it, or the bad index is a cache hit that fails identically on
        # every future run and `--force` becomes the only way out.
        manifest.pop(f"{city.id}/{index_artefact.key}", None)
        index_path.unlink(missing_ok=True)
        raise

    tiles = select_tiles(index, source, region_bounds=region.bounds, region_crs=city.geodetic_crs)
    log.info(
        "  %s: %d of %d sheets overlap %s",
        source.id,
        len(tiles),
        len(index["features"]),
        region.id,
    )
    if not tiles:
        # Everything else in this module treats a silent no-op as the worst
        # outcome, and selecting zero sheets is the same class of failure:
        # wrong bounds, a wrong `index_crs`, or a renamed geometry key all land
        # here and would otherwise exit 0 with no buildings.
        raise ValueError(
            f"tiled source '{source.id}' selected no tiles for region '{region.id}'. "
            f"Check the region bounds and that `index_crs` matches the index's datum."
        )
    return tiles


def read_feature_collection(path: Path, where: str) -> dict[str, Any]:
    """Parse a fetched GeoJSON file, rejecting anything that is not a feature collection.

    A portal that answers a rate limit or an outage with HTTP 200 and a JSON
    error body would otherwise be cached as a valid document with zero
    features, and every later run would be a clean cache hit that quietly
    produced nothing — no buildings, or no fare nodes.

    Public because both kinds of GeoJSON the pipeline fetches from the same
    portal need the same guard: the buildings sheet index and the fare-node
    point datasets.
    """
    try:
        document = json.loads(path.read_bytes())
    except json.JSONDecodeError as error:
        raise ValueError(f"{where}: {path} is not JSON: {error}") from error

    if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
        raise ValueError(
            f"{where}: {path} is not a GeoJSON FeatureCollection. The publisher may have "
            f"returned an error page with a 200 status."
        )
    if not isinstance(document.get("features"), list) or not document["features"]:
        raise ValueError(f"{where}: {path} contains no features")
    return document


def _check_source_names(city: CityConfig, only: set[str]) -> None:
    """Reject an unknown `--only` name rather than fetching nothing.

    A typo would otherwise look exactly like a successful run with everything
    already cached, which is the sort of thing you notice three tasks later.
    """
    known = city.source_ids
    unknown = only - known
    if unknown:
        raise KeyError(
            f"City '{city.id}' has no source(s): {', '.join(sorted(unknown))}. "
            f"Known: {', '.join(sorted(known))}"
        )


def _process(
    artefact: Artefact,
    city: CityConfig,
    root: Path,
    manifest: dict[str, Any],
    report: FetchReport,
    *,
    force: bool,
    dry_run: bool,
) -> None:
    manifest_key = f"{city.id}/{artefact.key}"
    destination = artefact_path(city.id, artefact, root=root)

    # `--force` overrides fetch-once, not the publisher's own version stamp.
    # A versioned artefact still consults its stamp, so re-snapshotting six
    # sheets after one was republished costs one sheet rather than 265 MB.
    # Unversioned artefacts have nothing to consult and always re-download.
    ignore_cache = force and artefact.version is None
    if not ignore_cache and _is_cached(manifest.get(manifest_key), destination, artefact.version):
        log.info("  cached   %s", manifest_key)
        report.cached.append(manifest_key)
        return

    if dry_run:
        log.info("  would fetch %s  <- %s", manifest_key, redact(artefact.url))
        report.downloaded.append(manifest_key)
        return

    log.info("  fetching %s", manifest_key)
    size, sha256 = download(artefact.url, destination)
    manifest[manifest_key] = {
        # Redacted: see `redact`. Re-derived from config or the index each run,
        # so nothing depends on this being complete.
        "url": redact(artefact.url),
        "path": str(destination.relative_to(root)),
        "size": size,
        # Provenance only — `_is_cached` validates on size and version. Recorded
        # because it is free here and is what lets a sheet be checked against the
        # publisher's own download, which is how the datum question was settled.
        "sha256": sha256,
        "version": artefact.version,
        "fetched_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    if artefact.kind is ArtefactKind.INDEX:
        report.indexes.append(manifest_key)
    else:
        report.downloaded.append(manifest_key)
    report.total_bytes += size


def main(argv: list[str] | None = None) -> int:
    # `__doc__` is None under `python -OO`.
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--city", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument(
        "--only",
        nargs="+",
        metavar="SOURCE",
        help="fetch only these sources, by config key",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "take a fresh snapshot: re-fetch unversioned sources, and re-read each "
            "index so versioned tiles re-download only where the revision moved"
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report the plan without downloading payload (indexes are still fetched)",
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    city = load_city(args.city)
    log.info("%s / %s", city.name, city.region(args.region).name)
    report = fetch_city(
        city,
        args.region,
        force=args.force,
        only=set(args.only) if args.only else None,
        dry_run=args.dry_run,
    )
    if report.indexes:
        log.info("%d index(es) fetched", len(report.indexes))
    if args.dry_run:
        log.info(
            "%d artefacts: %d would be fetched, %d already cached",
            report.considered,
            len(report.downloaded),
            len(report.cached),
        )
    else:
        log.info(
            "%d artefacts: %d fetched (%.1f MB), %d cached",
            report.considered,
            len(report.downloaded),
            report.total_bytes / 1e6,
            len(report.cached),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
