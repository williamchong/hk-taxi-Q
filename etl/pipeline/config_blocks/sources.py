"""`sources:` — the paged and tiled publishers a stage fetches from.

One of `pipeline.config`'s blocks (`P3-35f`, `Q133`) — moved whole, and imported
through `pipeline.config`, which re-exports every name here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pipeline.config_blocks.base import _require


@dataclass(frozen=True)
class PagedSource:
    """A dataset served a page of records at a time, from one fixed query.

    The third shape after `sources` and `tiled_sources`, and it is not a variant
    of either: a plain source is one request for one file, a tiled source is an
    *index* that says which files a region needs, and this is one file the
    publisher will only hand over in instalments.

    🔴 **Whole-territory on purpose, never a bbox.** The obvious alternative is
    to ask the publisher for the region and skip the paging entirely — it is one
    request and a hundredth of the bytes. It is refused because `sources` is
    per-**city** while an envelope is per-**region**, so a bbox URL cannot be
    declared here without either duplicating bounds that hard rule 3 says live
    in one place, or inventing a per-region source block. The region clip stays
    where it already is: `bbox` at read time, from config.

    ⚠️ **`url` is a template, not an address.** It carries `{offset}` and
    `{count}`; `fetch.download_paged` walks it and assembles one file, so
    nothing downstream knows this source was paged.
    """

    id: str
    url: str
    # The publisher's own `maxRecordCount`. Asking for more is silently capped,
    # so this is read from the service rather than chosen.
    page_size: int
    # A ceiling on requests, so a publisher ignoring `resultOffset` fails loudly.
    max_pages: int
    # What the assembled file is called. ⚠️ **Load-bearing for GeoJSON**:
    # `pyogrio` takes a layer's name from the filename stem, so this is what a
    # `layer:` elsewhere in the file has to match.
    filename: str


@dataclass(frozen=True)
class TiledSource:
    """A dataset published per map sheet, reachable only through an index.

    The index is a vector layer whose features carry both a footprint and the
    download URL for that footprint's models, so which sheets a region needs is
    derived rather than listed. The property names below are what keeps this
    city-agnostic: the pipeline knows "some property holds the URL", never that
    Hong Kong happens to call it `Format_glTF`.

    Those URLs may embed a publisher's API key, which is why they are read from
    the fetched index at run time and never written into config or the manifest.
    """

    id: str
    index_url: str
    # Datum of the index geometry, which need not match the region's.
    index_crs: str
    id_property: str
    url_property: str
    # Per-tile version stamp used as the cache key. Optional: a publisher that
    # offers none simply gets fetch-once semantics.
    revision_property: str | None = None
    # Filename suffix for downloaded tiles, for publishers whose download URL
    # path carries none (`/directDownload?productName=…&productFormat=FGDB`).
    # Without it such a tile would land as `<id>.bin`, which the zip-aware
    # readers refuse to route through `/vsizip/`.
    tile_suffix: str | None = None


def _paged_source(source_id: str, body: Any, where: str) -> PagedSource:
    """One `paged_sources` entry, checked at load (`Q94`).

    ⚠️ **The template is checked for its two placeholders here**, because a URL
    missing `{offset}` fetches page one repeatedly and only fails at
    `max_pages` — after twenty-two requests and a file of duplicates.
    """
    where = f"{where}:{source_id}"
    if not isinstance(body, dict):
        raise ValueError(f"{where} must be a mapping, got {body!r}")
    url = str(_require(body, "url", where))
    # ⚠️ **Formatted rather than searched, on `_tile_member`'s precedent** — that
    # validator makes the same check for `{tile}` and makes it this way. A
    # substring test passes a URL carrying a *third* placeholder, which then
    # fails inside `download_paged` on the first request rather than at load.
    try:
        url.format(offset=0, count=1)
    except (KeyError, IndexError, ValueError) as error:
        raise ValueError(
            f"{where}:url {url!r} allows only the {{offset}} and {{count}} placeholders ({error})"
        ) from error
    for placeholder in ("{offset}", "{count}"):
        if placeholder not in url:
            raise ValueError(f"{where}:url has no {placeholder} — it is a template, not an address")
    page_size = int(_require(body, "page_size", where))
    max_pages = int(_require(body, "max_pages", where))
    if page_size < 1:
        raise ValueError(f"{where}:page_size is {page_size}, which asks for nothing")
    if max_pages < 1:
        raise ValueError(f"{where}:max_pages is {max_pages}, which walks nowhere")
    filename = str(_require(body, "filename", where))
    # ⚠️ **The same rule as `fetch._safe_segment`'s, restated because the import
    # direction forbids sharing it**: `fetch` imports `config`, so `config`
    # cannot reach back. Restated *exactly*, null byte included — an earlier
    # version of this check omitted it and was a strictly weaker path-escape
    # guard than the one the repo already had.
    if filename in {".", ".."} or set(filename) & {"/", "\\", "\0"}:
        raise ValueError(f"{where}:filename {filename!r} is not a plain filename")
    return PagedSource(
        id=source_id, url=url, page_size=page_size, max_pages=max_pages, filename=filename
    )


def _extra_cas(values: Any, path: Path) -> tuple[Path, ...]:
    """CA certificate paths, resolved against the yaml's own directory.

    Each must exist at load: a fetch that quietly fell back to the default
    store would re-surface the publisher's broken chain as a mid-run download
    failure, hundreds of megabytes in.
    """
    if not values:
        return ()
    resolved: list[Path] = []
    for value in values:
        candidate = (path.parent / str(value)).resolve()
        if not candidate.is_file():
            raise ValueError(f"{path}:extra_cas names {value!r}, which does not exist")
        resolved.append(candidate)
    return tuple(resolved)


def _tiled_source(source_id: str, body: dict[str, Any], path: Path) -> TiledSource:
    where = f"{path}:tiled_sources.{source_id}"
    revision = body.get("revision_property")
    suffix = body.get("tile_suffix")
    if suffix is not None:
        suffix = str(suffix)
        if not suffix.startswith("."):
            raise ValueError(f"{where}:tile_suffix is {suffix!r}, expected a '.suffix'")
    return TiledSource(
        id=source_id,
        index_url=str(_require(body, "index_url", where)),
        index_crs=str(_require(body, "index_crs", where)),
        id_property=str(_require(body, "id_property", where)),
        url_property=str(_require(body, "url_property", where)),
        revision_property=None if revision is None else str(revision),
        tile_suffix=suffix,
    )
