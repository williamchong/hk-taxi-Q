"""Source fetching tests.

The network is never touched: `download` is replaced with a stub that writes
known bytes. What is worth testing here is the *decisions* — which tiles a
region selects, and whether a second run does nothing — not urllib.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import pytest

from pipeline import fetch
from pipeline.config import CITIES_ROOT, TiledSource, load_city
from pipeline.crs import GeodeticBounds

# Wan Chai, per docs/DATA_SOURCES.md. Stated here rather than read from the
# config so a config change cannot quietly move what these tests assert.
WAN_CHAI = GeodeticBounds(west=114.172, east=114.188, south=22.276, north=22.284)

BUILDINGS = TiledSource(
    id="buildings",
    index_url="https://example.test/index",
    index_crs="EPSG:4326",
    id_property="SHEETNO",
    url_property="Format_glTF",
    revision_property="REVISIONDATE",
)


def sheet(name: str, west: float, south: float, size: float = 0.008) -> dict[str, Any]:
    east, north = west + size, south + size
    return {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [
                [[west, south], [east, south], [east, north], [west, north], [west, south]]
            ],
        },
        "properties": {
            "SHEETNO": name,
            "REVISIONDATE": "20250929",
            "Format_glTF": f"https://example.test/api/3d-zip/GLTF0/{name}.zip?key=SECRET",
            # The topography source reads this one — keyless, and with the
            # format in the query string rather than the URL path, per the
            # publisher shape `tile_suffix` exists for.
            "FGDB": f"https://example.test/OpenData/directDownload?sheetName=T{name}&productFormat=FGDB",
        },
    }


def index_of(*features: dict[str, Any]) -> dict[str, Any]:
    return {"type": "FeatureCollection", "features": list(features)}


OVERLAPPING = sheet("OVERLAP", 114.176, 22.278)
DISTANT = sheet("DISTANT", 114.300, 22.400)


class TestSelectTiles:
    def select(self, index: dict[str, Any], crs: str = "EPSG:4326") -> list[str]:
        tiles = fetch.select_tiles(index, BUILDINGS, region_bounds=WAN_CHAI, region_crs=crs)
        return [tile.key for tile in tiles]

    def test_selects_only_overlapping_sheets(self) -> None:
        assert self.select(index_of(OVERLAPPING, DISTANT)) == ["buildings/OVERLAP"]

    def test_sheet_touching_the_region_edge_is_selected(self) -> None:
        """Sheets tile the territory edge to edge, so a region boundary landing
        exactly on a shared edge must not fall down the crack between them."""
        touching = sheet("TOUCHING", WAN_CHAI.east, 22.278)
        assert "buildings/TOUCHING" in self.select(index_of(touching))

    def test_reading_the_region_on_the_wrong_datum_selects_different_sheets(self) -> None:
        """The ~304 m HK1980/WGS84 shift, reproduced as a selection difference.

        This is not theoretical: it is the mistake documented in
        DATA_SOURCES.md, where two readings of the same four numbers disagreed
        on a third of the region.

        The sheet below sits just off the region's eastern edge. Read as WGS84
        the region does not reach it; read as HK1980 the whole region shifts
        east onto it. Same four numbers, different map.
        """
        marginal = sheet("MARGINAL", 114.1885, 22.278, size=0.002)
        assert self.select(index_of(marginal), crs="EPSG:4326") == []
        assert self.select(index_of(marginal), crs="EPSG:4611") == ["buildings/MARGINAL"]

    def test_multipolygon_geometry_is_understood(self) -> None:
        multi = sheet("MULTI", 114.176, 22.278)
        multi["geometry"] = {
            "type": "MultiPolygon",
            "coordinates": [multi["geometry"]["coordinates"]],
        }
        assert self.select(index_of(multi)) == ["buildings/MULTI"]

    def test_geometryless_feature_is_skipped(self) -> None:
        broken = {"type": "Feature", "geometry": None, "properties": {}}
        assert self.select(index_of(broken, OVERLAPPING)) == ["buildings/OVERLAP"]

    def test_missing_property_on_a_selected_sheet_is_an_error(self) -> None:
        """Schema drift must stop the build rather than silently fetch nothing."""
        renamed = sheet("RENAMED", 114.176, 22.278)
        renamed["properties"]["Format_GLTF"] = renamed["properties"].pop("Format_glTF")
        with pytest.raises(ValueError, match="Format_glTF"):
            self.select(index_of(renamed))

    def test_missing_property_outside_the_region_is_ignored(self) -> None:
        """The index covers the whole territory. One malformed sheet in a
        district we never visit is not our problem."""
        broken = sheet("BROKEN", 114.300, 22.400)
        del broken["properties"]["Format_glTF"]
        assert self.select(index_of(broken, OVERLAPPING)) == ["buildings/OVERLAP"]

    def test_tile_url_and_revision_are_carried_through(self) -> None:
        tiles = fetch.select_tiles(
            index_of(OVERLAPPING), BUILDINGS, region_bounds=WAN_CHAI, region_crs="EPSG:4326"
        )
        assert tiles[0].version == "20250929"
        assert tiles[0].url.endswith("OVERLAP.zip?key=SECRET")
        assert tiles[0].path == Path("buildings/OVERLAP.zip")

    def test_tiles_are_named_after_their_id_not_their_url(self) -> None:
        """Two sheets can share a URL basename and differ only in the query
        string. Named after the basename they would overwrite each other, and
        each would invalidate the other's cache entry on every run."""
        first = sheet("ALPHA", 114.176, 22.278)
        second = sheet("BETA", 114.178, 22.279)
        for feature, name in ((first, "ALPHA"), (second, "BETA")):
            feature["properties"]["Format_glTF"] = f"https://example.test/download?sheet={name}"

        tiles = fetch.select_tiles(
            index_of(first, second), BUILDINGS, region_bounds=WAN_CHAI, region_crs="EPSG:4326"
        )
        assert len({tile.path for tile in tiles}) == 2

    def test_a_configured_suffix_wins_over_the_urls(self) -> None:
        """A publisher whose download URL carries its format in the query
        string offers no suffix to inherit — the tile would land as `.bin`,
        which the zip-aware readers refuse to route through `/vsizip/`."""
        feature = sheet("ALPHA", 114.176, 22.278)
        feature["properties"]["Format_glTF"] = (
            "https://example.test/OpenData/directDownload?sheetName=TALPHA&productFormat=FGDB"
        )
        suffixed = replace(BUILDINGS, id="topography", tile_suffix=".zip")

        tiles = fetch.select_tiles(
            index_of(feature), suffixed, region_bounds=WAN_CHAI, region_crs="EPSG:4326"
        )
        assert tiles[0].path == Path("topography/ALPHA.zip")

    def test_without_a_configured_suffix_the_urls_still_decides(self) -> None:
        tiles = fetch.select_tiles(
            index_of(OVERLAPPING), BUILDINGS, region_bounds=WAN_CHAI, region_crs="EPSG:4326"
        )
        assert tiles[0].path == Path("buildings/OVERLAP.zip")


class TestRedact:
    def test_removes_the_api_key(self) -> None:
        assert fetch.redact("https://h.test/a/b.zip?key=SECRET") == "https://h.test/a/b.zip"

    def test_removes_basic_auth_credentials(self) -> None:
        """The contract is 'no credential is ever recorded', not 'no key is'."""
        assert fetch.redact("https://u:pw@h.test/a.zip?key=S") == "https://h.test/a.zip"

    def test_keeps_a_non_default_port(self) -> None:
        assert fetch.redact("https://h.test:8443/a.zip?key=S") == "https://h.test:8443/a.zip"


class TestDownload:
    """Against a real socket. `download` is the one place where mocking the
    transport would mock away the behaviour under test."""

    @staticmethod
    def serve(body: bytes, declared_length: int | None = None) -> str:
        """One-shot local server; returns its URL. Closes early if it declares
        more than it sends."""

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                self.send_response(200)
                self.send_header("Content-Length", str(declared_length or len(body)))
                self.end_headers()
                self.wfile.write(body)
                self.wfile.flush()
                self.close_connection = True

            def log_message(self, *args: Any) -> None:
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.handle_request, daemon=True).start()
        return f"http://127.0.0.1:{server.server_address[1]}/sheet.zip"

    def test_complete_response_is_written(self, tmp_path: Path) -> None:
        destination = tmp_path / "sheet.zip"
        size, digest = fetch.download(self.serve(b"payload"), destination)
        assert size == 7
        assert destination.read_bytes() == b"payload"
        assert digest == hashlib.sha256(b"payload").hexdigest()

    def test_short_response_is_refused_and_leaves_no_file(
        self, tmp_path: Path, monkeypatch
    ) -> None:
        """`read(amt)` returns b'' on a premature close rather than raising, so
        without an explicit length check a truncated sheet is committed and then
        cached at its short size forever.
        """
        monkeypatch.setattr(fetch, "_RETRY_BACKOFF_S", 0.0)
        destination = tmp_path / "sheet.zip"
        with pytest.raises(RuntimeError, match="after 3 attempts"):
            fetch.download(self.serve(b"x" * 5000, declared_length=1_000_000), destination)
        assert not destination.exists()
        assert not list(tmp_path.glob("*.part"))


class TestUntrustedUrls:
    """Tile URLs are read out of a downloaded index, so they are input, not code."""

    def test_non_http_scheme_is_refused(self, tmp_path: Path) -> None:
        with pytest.raises(ValueError, match="not http"):
            fetch.download("file:///etc/passwd", tmp_path / "out.bin")

    def test_filename_cannot_escape_the_sources_tree(self) -> None:
        assert fetch._filename_for("https://h.test/a/../../etc/passwd", "fb") == "passwd"
        # A trailing slash normalises away rather than yielding an empty name.
        assert fetch._filename_for("https://h.test/dir/", "fallback.zip") == "dir"
        assert fetch._filename_for("https://h.test", "fallback.zip") == "fallback.zip"

    def test_unusable_filename_is_an_error_not_a_guess(self) -> None:
        with pytest.raises(ValueError, match="safe filename"):
            fetch._filename_for("https://h.test/", "..")


@pytest.fixture
def offline(monkeypatch, tmp_path: Path):
    """Replace the network with a stub, and count what it was asked for."""
    fetched: list[str] = []

    def _download(url: str, destination: Path, **_: Any) -> tuple[int, str]:
        fetched.append(url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = (
            json.dumps(index_of(OVERLAPPING, DISTANT)).encode()
            if destination.name == "index.geojson"
            else b"model-bytes"
        )
        destination.write_bytes(payload)
        return len(payload), hashlib.sha256(payload).hexdigest()

    def _download_paged(template: str, destination: Path, spec: Any, **_: Any) -> tuple[int, str]:
        """The paged walk, stubbed on the same terms (`Q94`).

        🔴 **Required, not tidiness.** `fetch_city` runs against the real Hong
        Kong config, which declares a paged source since `Q94`; without this the
        suite reaches the live CSDI service and hangs for however long 22 pages
        and 163 MB take.
        """
        return _download(template.format(offset=0, count=spec.size), destination)

    monkeypatch.setattr(fetch, "download", _download)
    monkeypatch.setattr(fetch, "download_paged", _download_paged)
    return fetched


@pytest.fixture
def city():
    return load_city("hong_kong", cities_root=CITIES_ROOT)


class TestFetchCity:
    """Exercised against the real Hong Kong config, with the network stubbed —
    so these also check that config actually drives the fetcher."""

    def test_first_run_fetches_roads_index_and_selected_sheets(self, city, offline, tmp_path):
        report = fetch_once(city, tmp_path)
        assert "hong_kong/buildings/OVERLAP" in report.downloaded
        assert "hong_kong/buildings/DISTANT" not in report.downloaded
        assert "hong_kong/road_network_gdb" in report.downloaded
        assert not report.cached

    def test_second_run_downloads_nothing(self, city, offline, tmp_path):
        """The acceptance criterion for P1-1."""
        first = fetch_once(city, tmp_path)
        offline.clear()
        second = fetch_once(city, tmp_path)
        assert not second.downloaded
        # The index counts too: fetched on the first run, cached on the second.
        assert len(second.cached) == len(first.downloaded) + len(first.indexes)
        assert offline == []

    def test_force_refetches_unversioned_sources_but_respects_revisions(
        self, city, offline, tmp_path
    ):
        """`--force` overrides fetch-once, not the publisher's version stamp.

        Otherwise re-snapshotting after a single sheet was republished would
        re-download all six — 265 MB to collect 44 MB of change.
        """
        fetch_once(city, tmp_path)
        report = fetch_once(city, tmp_path, force=True)
        assert "hong_kong/road_network_gdb" in report.downloaded
        assert "hong_kong/buildings/OVERLAP" in report.cached

    def test_force_repulls_a_sheet_whose_revision_moved(self, city, offline, tmp_path):
        fetch_once(city, tmp_path)
        manifest_path = tmp_path / fetch.MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text())
        manifest["hong_kong/buildings/OVERLAP"]["version"] = "20200101"
        manifest_path.write_text(json.dumps(manifest))

        report = fetch_once(city, tmp_path, force=True)
        assert "hong_kong/buildings/OVERLAP" in report.downloaded

    def test_artefact_of_the_wrong_size_is_refetched(self, city, offline, tmp_path):
        """A file whose size disagrees with the manifest is not a cache hit.

        The stronger guarantee — that a short download never *becomes* the
        manifest's recorded size — lives in `TestDownload`, since it has to be
        enforced before the file is committed rather than detected afterwards.
        """
        fetch_once(city, tmp_path)
        (tmp_path / "hong_kong" / "road_data_dictionary" / "rdnet_dataspec.zip").write_bytes(b"cut")
        assert "hong_kong/road_data_dictionary" in fetch_once(city, tmp_path).downloaded

    def test_a_failure_partway_through_keeps_what_already_succeeded(
        self, city, monkeypatch, tmp_path
    ):
        """One dropped connection must not cost the whole snapshot.

        Without the manifest being written in a `finally`, a failure on the last
        sheet discards the record of the five that landed, and the next run
        re-downloads ~283 MB it already has.
        """
        ok: list[str] = []

        def _download(url: str, destination: Path, **_: Any) -> tuple[int, str]:
            if destination.name == "RdNet_IRNP.gdb.zip":
                raise RuntimeError("connection reset")
            destination.parent.mkdir(parents=True, exist_ok=True)
            payload = (
                json.dumps(index_of(OVERLAPPING, DISTANT)).encode()
                if destination.name == "index.geojson"
                else b"model-bytes"
            )
            destination.write_bytes(payload)
            ok.append(destination.name)
            return len(payload), hashlib.sha256(payload).hexdigest()

        monkeypatch.setattr(fetch, "download", _download)
        with pytest.raises(RuntimeError, match="connection reset"):
            fetch_once(city, tmp_path)

        manifest = json.loads((tmp_path / fetch.MANIFEST_NAME).read_text())
        assert ok, "expected some artefacts to have downloaded before the failure"
        assert len(manifest) == len(ok)
        assert "hong_kong/road_network_gdb" not in manifest

    def test_new_revision_invalidates_one_sheet(self, city, offline, tmp_path):
        """REVISIONDATE is per sheet, so a republished sheet must not drag its
        unchanged neighbours down with it."""
        fetch_once(city, tmp_path)
        manifest_path = tmp_path / fetch.MANIFEST_NAME
        manifest = json.loads(manifest_path.read_text())
        manifest["hong_kong/buildings/OVERLAP"]["version"] = "20200101"
        manifest_path.write_text(json.dumps(manifest))

        report = fetch_once(city, tmp_path)
        assert report.downloaded == ["hong_kong/buildings/OVERLAP"]

    def test_only_limits_the_fetch(self, city, offline, tmp_path):
        report = fetch_once(city, tmp_path, only={"road_data_dictionary"})
        assert report.downloaded == ["hong_kong/road_data_dictionary"]

    def test_unknown_only_name_is_rejected(self, city, offline, tmp_path):
        """Silently fetching nothing looks identical to a fully cached run."""
        with pytest.raises(KeyError, match="road_rundabouts"):
            fetch_once(city, tmp_path, only={"road_rundabouts"})

    def test_manifest_never_records_the_api_key(self, city, offline, tmp_path):
        fetch_once(city, tmp_path)
        assert "SECRET" not in (tmp_path / fetch.MANIFEST_NAME).read_text()


class TestDryRun:
    def test_downloads_the_index_but_no_payload(self, city, offline, tmp_path):
        """The index is the one thing a dry run fetches, because without it
        there are no tile names to report."""
        report = fetch_once(city, tmp_path, dry_run=True)

        assert (tmp_path / "hong_kong" / "buildings" / "index.geojson").exists()
        assert not (tmp_path / "hong_kong" / "buildings" / "OVERLAP.zip").exists()
        assert not (tmp_path / "hong_kong" / "road_network_gdb").exists()
        assert "hong_kong/buildings/OVERLAP" in report.downloaded

    def test_reports_the_index_as_fetched_not_as_hypothetical(self, city, offline, tmp_path):
        """It really did touch the disk; saying otherwise would be a lie."""
        report = fetch_once(city, tmp_path, dry_run=True)
        assert report.indexes == ["hong_kong/buildings/index", "hong_kong/topography/index"]
        assert "hong_kong/buildings/index" not in report.downloaded

    def test_a_later_real_run_reuses_the_index(self, city, offline, tmp_path):
        fetch_once(city, tmp_path, dry_run=True)
        offline.clear()
        report = fetch_once(city, tmp_path)
        assert not report.indexes
        assert "hong_kong/buildings/index" in report.cached


class TestBadIndex:
    """A portal answering an outage with HTTP 200 and a JSON error body."""

    @pytest.fixture
    def serving(self, monkeypatch):
        def _serve(payload: bytes):
            def _download(url: str, destination: Path, **_: Any) -> tuple[int, str]:
                destination.parent.mkdir(parents=True, exist_ok=True)
                body = payload if destination.name == "index.geojson" else b"model-bytes"
                destination.write_bytes(body)
                return len(body), hashlib.sha256(body).hexdigest()

            monkeypatch.setattr(fetch, "download", _download)

        return _serve

    def test_error_body_is_rejected_not_cached_as_empty(self, city, serving, tmp_path):
        """Otherwise run 1 exits 0 with no buildings and every later run is a
        clean cache hit on the poisoned index."""
        serving(json.dumps({"error": "rate limited", "code": 429}).encode())
        with pytest.raises(ValueError, match="FeatureCollection"):
            fetch_once(city, tmp_path)

    def test_rejected_index_is_evicted_so_a_retry_can_work(self, city, serving, tmp_path):
        serving(json.dumps({"error": "rate limited"}).encode())
        with pytest.raises(ValueError):
            fetch_once(city, tmp_path)

        manifest = json.loads((tmp_path / fetch.MANIFEST_NAME).read_text())
        assert "hong_kong/buildings/index" not in manifest
        assert not (tmp_path / "hong_kong" / "buildings" / "index.geojson").exists()

    def test_unparseable_index_names_the_source(self, city, serving, tmp_path):
        serving(b"<html>503 Service Unavailable</html>")
        with pytest.raises(ValueError, match="buildings"):
            fetch_once(city, tmp_path)

    def test_selecting_no_tiles_is_an_error(self, city, serving, tmp_path):
        """Wrong bounds or a wrong index_crs would otherwise exit 0 with no
        buildings, which is the silent no-op this module refuses everywhere."""
        serving(json.dumps(index_of(DISTANT)).encode())
        with pytest.raises(ValueError, match="selected no tiles"):
            fetch_once(city, tmp_path)


def fetch_once(city, root: Path, **kwargs):
    return fetch.fetch_city(city, "wan_chai", root=root, **kwargs)


@pytest.mark.skipif(
    not (fetch.source_dir("hong_kong", "buildings") / fetch.INDEX_NAME).exists(),
    reason="requires a fetched sheet index",
)
def test_real_index_selects_the_six_documented_sheets(hong_kong) -> None:
    """Against the live index, not a fixture.

    docs/DATA_SOURCES.md names these six as covering the region. They are not
    configured anywhere — the point is that intersecting the bounds with the
    published index re-derives exactly that list.

    Through `cached_tiles` because that is what `buildings.py` calls, so this
    exercises the real path rather than an equivalent one assembled here.
    """
    tiles = fetch.cached_tiles(
        hong_kong, hong_kong.region("wan_chai"), hong_kong.tiled_sources["buildings"]
    )
    assert sorted(tile.tile_id for tile in tiles) == [
        "11-SW-10C",
        "11-SW-10D",
        "11-SW-14B",
        "11-SW-15A",
        "11-SW-15B",
        "11-SW-9D",
    ]


class TestDownloadPaged:
    """`Q94`: walking a publisher that serves one page of records at a time.

    Against a real socket, on `TestDownload`'s argument — the transport is part
    of what is under test, and the walk's stop condition comes off the wire.
    """

    @staticmethod
    def serve(pages: list[dict[str, Any]]) -> tuple[str, list[int]]:
        """Serve `pages` in order, one per request. Returns (template, offsets seen)."""
        seen: list[int] = []

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                offset = int(self.path.rsplit("offset=", 1)[1].split("&")[0])
                seen.append(offset)
                body = json.dumps(pages[min(len(seen) - 1, len(pages) - 1)]).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args: Any) -> None:
                pass

        server = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]
        return f"http://127.0.0.1:{port}/q?offset={{offset}}&count={{count}}", seen

    @staticmethod
    def _page(n: int, crs: str = "EPSG:2326") -> dict[str, Any]:
        return {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": crs}},
            "features": [{"type": "Feature", "properties": {"i": i}} for i in range(n)],
        }

    def test_it_walks_until_a_short_page_and_assembles_one_file(self, tmp_path: Path) -> None:
        url, seen = self.serve([self._page(3), self._page(3), self._page(1)])
        destination = tmp_path / "out.geojson"
        size, digest = fetch.download_paged(url, destination, fetch.PageSpec(size=3, max_pages=10))
        document = json.loads(destination.read_text())
        assert len(document["features"]) == 7
        assert seen == [0, 3, 6]
        assert document["crs"]["properties"]["name"] == "EPSG:2326"
        assert size == destination.stat().st_size
        assert digest == hashlib.sha256(destination.read_bytes()).hexdigest()

    def test_a_publisher_that_never_shortens_is_refused_rather_than_walked_forever(
        self, tmp_path: Path
    ) -> None:
        """🔴 The failure `max_pages` exists for: a service ignoring `resultOffset`
        returns page one every time, and without a ceiling the walk fills the disk
        with duplicates and never ends."""
        url, _ = self.serve([self._page(3)])
        destination = tmp_path / "out.geojson"
        with pytest.raises(ValueError, match="did not end within 4 pages"):
            fetch.download_paged(url, destination, fetch.PageSpec(size=3, max_pages=4))
        assert not destination.exists()
        assert not list(tmp_path.glob("*.part"))

    def test_a_CRS_change_mid_walk_is_refused(self, tmp_path: Path) -> None:
        """A datum shift looks plausible and moves coordinates hundreds of metres."""
        url, _ = self.serve([self._page(3), self._page(1, crs="EPSG:4326")])
        with pytest.raises(ValueError, match="changed CRS mid-walk"):
            fetch.download_paged(
                url, tmp_path / "out.geojson", fetch.PageSpec(size=3, max_pages=10)
            )

    def test_an_error_payload_is_refused_rather_than_written(self, tmp_path: Path) -> None:
        """ArcGIS answers 200 with an `error` body, so the status code says nothing."""
        url, _ = self.serve([{"error": {"code": 400, "message": "Invalid where"}}])
        with pytest.raises(ValueError, match="returned"):
            fetch.download_paged(
                url, tmp_path / "out.geojson", fetch.PageSpec(size=3, max_pages=10)
            )

    def test_an_empty_layer_still_writes_a_valid_collection(self, tmp_path: Path) -> None:
        url, _ = self.serve([self._page(0)])
        destination = tmp_path / "out.geojson"
        fetch.download_paged(url, destination, fetch.PageSpec(size=3, max_pages=10))
        assert json.loads(destination.read_text())["features"] == []

    def test_an_interrupted_walk_leaves_no_half_file(self, tmp_path: Path) -> None:
        """The `.part`-then-rename discipline, one level up from `download`'s."""
        url, _ = self.serve([self._page(3), {"error": {"code": 500}}])
        destination = tmp_path / "out.geojson"
        with pytest.raises(ValueError):
            fetch.download_paged(url, destination, fetch.PageSpec(size=3, max_pages=10))
        assert not destination.exists()
        assert not list(tmp_path.glob("*.part"))
