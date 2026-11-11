"""`tools/make_parked.py` — the parked roster's library (`P3-72`, `Q161`).

What is pinned: the committed bytes against the generator, so an edit to a
proportion is a rebuild; every kind's footprint against the one
`hong_kong.yaml` places by, because the ETL stands a vehicle by those two
numbers and the engine draws the mesh, and a kind whose two disagree is a car
drawn through the kerb; the frame (nose north, ground at zero, centred);
the material door every part goes through; and the winding, for the reason
`test_make_vehicle.py` gives — wound inward, a wheel renders as a hole.
"""

from __future__ import annotations

import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from pipeline.config import load_config
from pipeline.gltf import MeshData

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

from make_parked import (  # noqa: E402
    GLINT,
    LIBRARY_FILE,
    NT_TAXI_GREEN,
    ROSTER,
    SHAPES,
    SURROUND_M,
    TAXI_MIRROR_REACH_M,
    WHEEL_SEGMENTS,
    WHITE,
    Glass,
    Shape,
    Taxi,
    _axle_zs,
    _doors,
    _end_panes,
    _glasshouse,
    _glazing,
    _liveried,
    _lower,
    _side_fixtures,
    _slab,
    _slab_glass,
    _slab_upper,
    _wheels,
    _window_bars,
    build_roster,
    deck_y_at,
    waist_y_at,
    write_roster,
)
from make_vehicle import (  # noqa: E402
    CIRCUIT_HEADLAMP,
    CIRCUIT_SIDELAMP,
    GLASS,
    KERB_SIDE,
    LAMP,
    MARKER_CABIN,
    MARKER_CABIN_DIM,
    MARKER_GLASS,
    MARKER_LAMP,
    MARKER_LIVERY,
    MARKER_PAINT,
    MATERIAL_OF_PAYLOAD,
    RED,
    SILVER,
    Chassis,
    Proportions,
    _wheel,
    material_parts,
    taxi_body,
    taxi_door,
    taxi_parts,
)

SHIPPED = ROOT / "game" / "assets" / "authored" / "vehicles"
TAXIS = frozenset({"taxi", "taxi_nt", "taxi_lantau"})
GLINTED = frozenset({"bus", "tram"})
# `ART_DESIGN.md`'s upper bar per vehicle.
TRIANGLE_CEILING = 2000
# The library's footprint may differ from the config's by this much: a wheel
# of ten segments does not reach its own radius exactly.
FOOTPRINT_SLACK_M = 0.05


def _shape(kind: str) -> Shape:
    """The lofted kind of that name."""
    return next(shape for shape in SHAPES if shape.kind == kind)


@pytest.fixture(scope="module")
def meshes() -> list[MeshData]:
    return build_roster()


@pytest.fixture(scope="module")
def by_name(meshes: list[MeshData]) -> dict[str, MeshData]:
    return {mesh.name: mesh for mesh in meshes}


class TestShippedAssets:
    def test_the_committed_library_matches_the_generator(self, tmp_path: Path) -> None:
        path, _, _ = write_roster(tmp_path)
        shipped = SHIPPED / LIBRARY_FILE
        assert shipped.exists(), f"{shipped.name} is not committed"
        assert shipped.read_bytes() == path.read_bytes(), (
            f"{shipped.name} is stale — re-run tools/make_parked.py"
        )


class TestTheFootprintIsTheConfigs:
    """🔴 The ETL places by `parked.vehicles:`; the engine draws this."""

    def test_every_config_kind_has_a_library_mesh(self, by_name: dict[str, MeshData]) -> None:
        city = load_config()
        assert city.parked is not None
        for vehicle in city.parked.vehicles.values():
            for mesh_name in vehicle.library_meshes:
                assert mesh_name in by_name, f"{vehicle.kind} names {mesh_name}, not in the library"

    def test_every_library_mesh_is_a_config_kind(self, by_name: dict[str, MeshData]) -> None:
        city = load_config()
        assert city.parked is not None
        named = {m for v in city.parked.vehicles.values() for m in v.library_meshes}
        assert set(by_name) == named

    def test_length_and_width_match_the_config(self, by_name: dict[str, MeshData]) -> None:
        city = load_config()
        assert city.parked is not None
        for vehicle in city.parked.vehicles.values():
            for mesh_name in vehicle.library_meshes:
                low, high = by_name[mesh_name].aabb()
                assert abs((high[0] - low[0]) - vehicle.width_m) <= FOOTPRINT_SLACK_M, mesh_name
                assert abs((high[2] - low[2]) - vehicle.length_m) <= FOOTPRINT_SLACK_M, mesh_name


class TestTheFrame:
    def test_the_ground_is_zero_and_the_body_is_centred(self, meshes: list[MeshData]) -> None:
        for mesh in meshes:
            low, high = mesh.aabb()
            assert abs(low[1]) < 1e-6, f"{mesh.name} floats {low[1]:.3f} m"
            assert low[0] < 0.0 < high[0] and low[2] < 0.0 < high[2], mesh.name

    def test_the_nose_is_north(self, meshes: list[MeshData]) -> None:
        """The head lamps sit at negative z, where `placed_positions` stands a
        bearing's nose: the one `LAMP`-coloured part on every lofted kind, and
        on a taxi — whose reversing lamps wear `LAMP` at the tail — the lenses
        on the head-lamp circuit."""
        for mesh in meshes:
            if mesh.name in TAXIS:
                lamp = mesh.uvs[:, 0] == CIRCUIT_HEADLAMP
            else:
                lamp = np.all(mesh.colours[:, :3] == np.array(LAMP, dtype=np.uint8), axis=1)
            assert lamp.any(), f"{mesh.name} has no head lamp"
            assert mesh.positions[lamp, 2].max() < 0.0, f"{mesh.name}'s lamps are not at the nose"


class TestTheBudget:
    def test_each_kind_is_under_the_ceiling(self, meshes: list[MeshData]) -> None:
        for mesh in meshes:
            assert mesh.triangle_count <= TRIANGLE_CEILING, mesh.name

    def test_each_kind_is_within_a_few_flat_colours(self, meshes: list[MeshData]) -> None:
        """`ART_DESIGN.md`'s 3 to 5, plus the three lens colours every vehicle
        carries, is the standing exception the taxi already holds. A green or
        blue licence (`Q183`) holds two more: the red taxi's tail lens is its
        paint and its roof is its chrome's silver, and theirs are not."""
        for mesh in meshes:
            colours = {tuple(int(v) for v in row[:3]) for row in mesh.colours}
            ceiling = 10 if mesh.name in ("taxi_nt", "taxi_lantau") else 8
            # The sky's streak in a window is one more.
            ceiling += mesh.name in GLINTED | TAXIS
            assert 3 <= len(colours) <= ceiling, f"{mesh.name} carries {len(colours)} colours"

    def test_every_part_goes_through_the_material_door(self, meshes: list[MeshData]) -> None:
        for mesh in meshes:
            group = material_parts(mesh)
            names = {part.material for part in group.parts}
            assert names <= set(MATERIAL_OF_PAYLOAD.values()), mesh.name
            assert "vehicle_paint" in names, mesh.name
            assert any(name.startswith("vehicle_lamp") for name in names), mesh.name


class TestLiveries:
    """`Q167`: a kind whose colour means something carries no livery panel,
    and every other kind's livery marks paint the palette can repaint."""

    IDENTITY = TAXIS | {"bus", "tram"}

    def test_a_colour_that_means_something_is_not_a_livery(
        self, by_name: dict[str, MeshData]
    ) -> None:
        for kind in self.IDENTITY:
            assert not np.any(by_name[kind].uvs[:, 1] == MARKER_LIVERY), kind

    def test_every_livery_marks_paint(self, by_name: dict[str, MeshData]) -> None:
        for shape in SHAPES:
            if shape.livery is None:
                assert shape.kind in self.IDENTITY, shape.kind
                continue
            mesh = by_name[shape.kind]
            marked = mesh.uvs[:, 1] == MARKER_LIVERY
            assert marked.any(), shape.kind
            # Only the livery's own colour, never a lens or the glass.
            assert np.all(mesh.colours[marked, :3] == np.array(shape.livery, dtype=np.uint8))

    def test_a_livery_on_no_painted_vertex_is_refused(self, by_name: dict[str, MeshData]) -> None:
        # The glass wears `GLASS` and is marked glass, so no paint matches it.
        shape = replace(_shape("car_a"), livery=GLASS)
        with pytest.raises(ValueError, match="no painted vertex"):
            _liveried(by_name["car_a"], shape)


# The kinds whose windows light at night, and at which level.
LIT_CABINS = {"minibus": MARKER_CABIN_DIM, "bus": MARKER_CABIN, "tram": MARKER_CABIN}


class TestCabins:
    """The windows that light at night are public transport's, all of them."""

    def test_only_public_transport_lights(self, by_name: dict[str, MeshData]) -> None:
        for kind, mesh in by_name.items():
            markers = set(mesh.uvs[:, 1].tolist()) & {MARKER_CABIN, MARKER_CABIN_DIM}
            assert markers == ({LIT_CABINS[kind]} if kind in LIT_CABINS else set()), kind

    def test_a_lit_cabin_leaves_no_dark_glass(self, by_name: dict[str, MeshData]) -> None:
        for kind in LIT_CABINS:
            mesh = by_name[kind]
            marked = mesh.uvs[:, 1] == LIT_CABINS[kind]
            assert not np.any(mesh.uvs[:, 1] == MARKER_GLASS), kind
            # The glass and the sky's streak in it, nothing else: not a pillar
            # or a blind on it.
            lit = {tuple(int(v) for v in row) for row in mesh.colours[marked, :3]}
            assert lit <= {GLASS, GLINT}, kind
            assert GLASS in lit, kind


def test_the_trams_one_head_lamp_is_on_the_circuit(by_name: dict[str, MeshData]) -> None:
    mesh = by_name["tram"]
    lit = mesh.uvs[:, 0] == CIRCUIT_HEADLAMP
    assert lit.any()
    assert np.all(mesh.uvs[lit, 1] == MARKER_LAMP)
    # On the dash's centreline, at the nose, where `_ends` stands it.
    low, high = mesh.positions[lit].min(axis=0), mesh.positions[lit].max(axis=0)
    assert low[0] == pytest.approx(-high[0])
    assert high[2] < 0.0


def test_the_trams_side_lamps_are_white_ahead_and_red_behind(
    by_name: dict[str, MeshData],
) -> None:
    mesh = by_name["tram"]
    lit = mesh.uvs[:, 0] == CIRCUIT_SIDELAMP
    assert np.all(mesh.uvs[lit, 1] == MARKER_LAMP)
    ahead, behind = lit & (mesh.positions[:, 2] < 0.0), lit & (mesh.positions[:, 2] > 0.0)
    assert np.all(mesh.colours[ahead, :3] == np.array(LAMP, dtype=np.uint8))
    assert np.all(mesh.colours[behind, :3] == np.array(RED, dtype=np.uint8))
    for end in (ahead, behind):
        assert {bool(x > 0.0) for x in mesh.positions[end, 0]} == {False, True}
    # No other kind has a side lamp to light, but the taxis: the player's body
    # carries its position lamps, which no moving car's instance data switches.
    for kind, other in by_name.items():
        if kind != "tram" and kind not in TAXIS:
            assert not np.any(other.uvs[:, 0] == CIRCUIT_SIDELAMP), kind


class TestWinding:
    @staticmethod
    def _outward_fraction(mesh: MeshData) -> float:
        centre = mesh.positions.mean(axis=0)
        face_normals = mesh.normals[mesh.triangles[:, 0]]
        return float((((mesh.triangle_centroids() - centre) * face_normals).sum(axis=1) > 0).mean())

    def test_no_triangle_is_degenerate(self, meshes: list[MeshData]) -> None:
        for mesh in meshes:
            areas = np.linalg.norm(mesh.triangle_cross(), axis=1)
            assert (areas > 1e-9).all(), f"{mesh.name} has {(areas <= 1e-9).sum()} degenerate"

    def test_every_loft_faces_outward(self) -> None:
        """The two lofts every body is built from are convex solids, so every
        face points away from their centre — wound the other way, `cull_back`
        renders the car as its own inside."""
        for shape in SHAPES:
            if shape.single_track:
                continue
            assert self._outward_fraction(_lower(shape)) == 1.0, shape.kind
            if shape.slab_sided:
                assert self._outward_fraction(_slab_upper(shape)) == 1.0, shape.kind
                continue
            assert (
                self._outward_fraction(
                    _glasshouse(
                        shape, shape.belt_y_m, shape.roof_y_m, shape.roof, name="g", cap=True
                    )
                )
                == 1.0
            ), shape.kind

    def test_every_body_encloses_a_positive_volume(self, meshes: list[MeshData]) -> None:
        """The signed volume of the whole mesh: inward-wound parts subtract."""
        for mesh in meshes:
            tri = mesh.positions[mesh.triangles]
            volume = (
                float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum()) / 6.0
            )
            low, high = mesh.aabb()
            box = float(np.prod(np.asarray(high) - np.asarray(low)))
            # A tenth: a motorcycle is mostly air and reads 0.12 of its box.
            assert volume > 0.1 * box, f"{mesh.name} encloses {volume:.2f} of a {box:.2f} m³ box"


class TestTheRoster:
    def test_the_kinds_are_distinct_and_named_after_their_shape(self) -> None:
        names = [entry.kind for entry in ROSTER]
        assert len(names) == len(set(names))
        for entry, mesh in zip(ROSTER, build_roster(), strict=True):
            assert mesh.name == entry.kind


class TestTheTaxis:
    """`P3-85`: a roster taxi is the player's die-cast body (`Q190`), shut and
    on its wheels, in its licence's paint."""

    def test_it_is_the_players_body_with_its_door_and_four_wheels(
        self, by_name: dict[str, MeshData]
    ) -> None:
        chassis, shape = Chassis(), Proportions()
        wheel = _wheel(
            chassis.wheel_radius_m,
            shape.wheel_width_m,
            WHEEL_SEGMENTS,
            faces=(1.0,),
            hub_slots=shape.hub_slots,
            name="w",
        )
        # `taxi_parts`, not `taxi_body`: the lettering is the player's car's alone (`Q202`).
        expected = (
            sum(part.triangle_count for part in taxi_parts(chassis, shape))
            + taxi_door(chassis, shape).triangle_count
            + 4 * wheel.triangle_count
        )
        for kind in TAXIS:
            assert by_name[kind].triangle_count == expected, kind

    def test_the_doorway_is_shut(self, by_name: dict[str, MeshData]) -> None:
        """The body leaves a hole in its kerb-side flank for the scene's
        swinging door; with the leaf in it, both flanks' planes are whole."""
        mesh = by_name["taxi"]
        half_width = Proportions().half_width_m
        areas = np.linalg.norm(mesh.triangle_cross(), axis=1) / 2.0
        corners = mesh.positions[mesh.triangles][:, :, 0]

        def skin_m2(side: float) -> float:
            in_plane = np.all(np.isclose(corners, side * half_width, atol=1e-6), axis=1)
            return float(areas[in_plane].sum())

        assert skin_m2(KERB_SIDE) == pytest.approx(skin_m2(-KERB_SIDE), abs=1e-4)
        assert skin_m2(KERB_SIDE) > 1.0

    def test_the_mirrors_stand_inside_the_footprint(self, by_name: dict[str, MeshData]) -> None:
        shape = Proportions()
        assert shape.mirror_reach_m > TAXI_MIRROR_REACH_M
        low, high = by_name["taxi"].aabb()
        players = taxi_body(Chassis(), shape).aabb()
        assert high[0] - low[0] < (players[1][0] - players[0][0]) - 0.2

    def test_a_licence_repaints_the_paint_and_never_a_lens(
        self, by_name: dict[str, MeshData]
    ) -> None:
        red = np.array(RED, dtype=np.uint8)
        urban, other = by_name["taxi"], by_name["taxi_nt"]
        was_red = np.all(urban.colours[:, :3] == red, axis=1)
        assert np.array_equal(urban.positions, other.positions)
        painted = was_red & (urban.uvs[:, 1] == MARKER_PAINT)
        assert painted.any()
        assert np.all(other.colours[painted, :3] == np.array(NT_TAXI_GREEN, dtype=np.uint8))
        # The brake lens is red on every licence.
        lens = was_red & (urban.uvs[:, 1] == MARKER_LAMP)
        assert lens.any()
        assert np.all(other.colours[lens, :3] == red)

    def test_a_white_roof_leaves_the_chrome_silver(self, by_name: dict[str, MeshData]) -> None:
        urban, other = by_name["taxi"], by_name["taxi_nt"]
        silver = np.all(urban.colours[:, :3] == np.array(SILVER, dtype=np.uint8), axis=1)
        whitened = silver & np.all(other.colours[:, :3] == np.array(WHITE, dtype=np.uint8), axis=1)
        kept = silver & ~whitened
        assert whitened.any() and kept.any()
        # The roof is paint; chrome keeps its trim marker.
        assert np.all(other.uvs[whitened, 1] == MARKER_PAINT)
        # Everything whitened is the greenhouse, above the belt; the grille,
        # bezels and hubcaps below it stay chrome.
        belt_y = Proportions().belt_y_m - Chassis().ground_y_m
        assert other.positions[whitened, 1].min() >= belt_y - 1e-6
        assert other.positions[kept, 1].min() < belt_y

    def test_the_roster_names_three_licences(self) -> None:
        assert {entry.kind for entry in ROSTER if isinstance(entry, Taxi)} == TAXIS


class TestTheDieCastPass:
    """`P3-85`: what each lofted kind carries off its 1:64 model."""

    def test_a_deck_falls_from_the_cabin_and_nowhere_else(self) -> None:
        falling = [shape for shape in SHAPES if shape.nose_drop_m or shape.tail_drop_m]
        assert {shape.kind for shape in falling} >= {"car_a", "car_b", "van"}
        for shape in falling:
            scuttle = shape.front_z_m + shape.cabin_front_m
            deck = shape.front_z_m + shape.cabin_rear_m
            assert deck_y_at(shape, (scuttle + deck) / 2.0) == shape.belt_y_m
            assert deck_y_at(shape, shape.body_front_z_m) == pytest.approx(
                shape.belt_y_m - shape.nose_drop_m
            )
            assert deck_y_at(shape, shape.body_rear_z_m) == pytest.approx(
                shape.belt_y_m - shape.tail_drop_m
            )
            lower = _lower(shape)
            ceiling = np.array([deck_y_at(shape, z) for z in lower.positions[:, 2]])
            assert np.all(lower.positions[:, 1] <= ceiling + 1e-6), shape.kind
            # The cap reaches its ceiling at both ends: nothing is left flat.
            nose = np.isclose(lower.positions[:, 2], shape.body_front_z_m)
            assert lower.positions[nose, 1].max() == pytest.approx(
                shape.belt_y_m - shape.nose_drop_m
            )

    def test_a_cabin_past_the_flank_refuses_a_falling_boot(self) -> None:
        with pytest.raises(ValueError, match="leaves the flank"):
            _lower(replace(_shape("car_b"), tail_drop_m=0.05))

    def test_a_deck_may_not_fall_below_its_lamps(self) -> None:
        with pytest.raises(ValueError, match="below its own lamps"):
            build_roster([replace(_shape("van"), nose_drop_m=0.25)])

    def test_doors_stand_on_the_kerb_side_clear_of_the_arches(self) -> None:
        doored = [shape for shape in SHAPES if shape.doors_m]
        assert {shape.kind for shape in doored} == {"minibus", "bus", "coach", "tram"}
        for shape in doored:
            parts = _doors(shape)
            assert parts, shape.kind
            for part in parts:
                assert np.all(np.sign(part.positions[:, 0]) == KERB_SIDE), part.name
                # In the skin: proud of the body, inside the footprint.
                assert np.abs(part.positions[:, 0]).max() < shape.half_width_m, part.name
            leaves = [part for part in parts if "_leaf_" in part.name]
            assert bool(leaves) == shape.door_glass, shape.kind

    def test_a_door_in_a_wheel_arch_is_refused(self) -> None:
        bus = _shape("bus")
        axle = bus.axles_m[0]
        with pytest.raises(ValueError, match="wheel arch"):
            _doors(replace(bus, doors_m=((axle - 0.2, axle + 1.0),)))

    def test_a_shut_line_stops_at_an_arch_crown(self) -> None:
        for shape in SHAPES:
            if not shape.shut_lines:
                continue
            lines = [part for part in _side_fixtures(shape) if part.name.startswith("shut_")]
            assert len(lines) == 2 * (shape.window_bays + 1), shape.kind
            crossed = 0
            for part in lines:
                z = float(part.positions[:, 2].mean())
                foot = float(part.positions[:, 1].min())
                over = any(abs(z - axle) <= shape.arch_radius_m for axle in _axle_zs(shape))
                assert foot >= (waist_y_at(shape, z) if over else shape.sill_y_m) - 1e-6, part.name
                crossed += over
            assert crossed, f"{shape.kind}: no shut line met an arch, so the rule went untested"

    def test_a_window_bar_lies_on_its_glass(self) -> None:
        barred = [shape for shape in SHAPES if shape.window_bar is not None]
        assert {shape.kind for shape in barred} == {"minibus"}
        for shape in barred:
            top = shape.roof_y_m
            g = _glazing(shape, shape.belt_y_m, top)
            bars = _window_bars(shape, shape.belt_y_m, top, name="deck")
            assert len(bars) == 2
            for bar in bars:
                assert g.panel_y < bar.positions[:, 1].min()
                assert bar.positions[:, 1].max() < g.glass_y
                z0, z1 = g.glass_top_z()
                assert bar.positions[:, 2].min() >= z0 - 1e-6
                assert bar.positions[:, 2].max() <= z1 + 1e-6

    def test_a_slotted_hubcap_costs_its_slots(self) -> None:
        shape = _shape("car_a")
        assert shape.hub_slots
        slotted = sum(part.triangle_count for part in _wheels(shape))
        plain = sum(part.triangle_count for part in _wheels(replace(shape, hub_slots=0)))
        # Three faces where one was, a slot a wheel face.
        assert slotted - plain == 4 * len(shape.axles_m) * 2 * shape.hub_slots


def test_the_lorry_is_a_cab_and_a_box_taller_than_it(by_name: dict[str, MeshData]) -> None:
    """`P3-85`'s one new kind: the box body stands behind the cab, over it,
    inside the footprint, and wears the cab's livery."""
    shape = _shape("lorry")
    mesh = by_name["lorry"]
    cab_rear = shape.front_z_m + shape.cabin_rear_m
    over_cab = mesh.positions[:, 1] > shape.roof_y_m + 1e-6
    assert over_cab.any()
    assert mesh.positions[over_cab, 2].min() > cab_rear
    assert np.abs(mesh.positions[over_cab, 0]).max() <= shape.half_width_m
    assert mesh.positions[over_cab, 2].max() <= shape.rear_z_m + 1e-6
    assert mesh.positions[over_cab, 1].max() == pytest.approx(shape.cargo_top_m)
    painted = over_cab & np.all(
        mesh.colours[:, :3] == np.array(shape.paint, dtype=np.uint8), axis=1
    )
    assert painted.any()
    assert np.all(mesh.uvs[painted, 1] == MARKER_LIVERY)


class TestFlatSides:
    """`P3-85`: the bus and the tram are one wall from the belt to a crowned
    roof, their windows applied run by run, as Tiny's models of them are —
    where two stacked glasshouses stepped in at each deck."""

    FLAT = ("bus", "tram")

    def test_the_double_deckers_are_flat_sided(self) -> None:
        assert {shape.kind for shape in SHAPES if shape.slab_sided} == set(self.FLAT)

    def test_the_wall_is_one_plane_a_flank_to_its_shoulder(self) -> None:
        for kind in self.FLAT:
            shape = _shape(kind)
            wall, b = _slab_upper(shape), _slab(shape)
            below = wall.positions[:, 1] <= b.shoulder_y + 1e-6
            # Under the shoulder a vertex is on the flank or on a corner cut's
            # inner edge, never between; over it the crown turns in.
            widths = np.abs(wall.positions[below, 0])
            assert np.all(np.isclose(widths, b.half_w) | np.isclose(widths, b.half_w - b.cut))
            assert (~below).any()
            assert np.abs(wall.positions[~below, 0]).max() < b.half_w

    def test_every_window_lies_on_its_flank_inside_the_skin(self) -> None:
        for kind in self.FLAT:
            shape = _shape(kind)
            b = _slab(shape)
            panes = _slab_glass(shape)
            assert panes, kind
            for pane in panes:
                assert np.abs(pane.positions[:, 0]).min() > b.half_w, pane.name
                assert np.abs(pane.positions[:, 0]).max() < shape.half_width_m, pane.name
                # A surround shows `SURROUND_M` round its run and no further.
                slack = SURROUND_M + 1e-6 if pane.name.startswith("surround_") else 1e-6
                assert pane.positions[:, 1].min() >= b.belt_y - slack, pane.name
                assert pane.positions[:, 1].max() < b.shoulder_y, pane.name
                front, rear = b.flank_z(float(pane.positions[:, 1].max()))
                assert pane.positions[:, 2].min() >= front - slack, pane.name
                assert pane.positions[:, 2].max() <= rear + slack, pane.name

    def test_a_window_off_the_flank_or_the_wall_is_refused(self) -> None:
        bus = _shape("bus")
        with pytest.raises(ValueError, match="off the flank"):
            _slab_glass(replace(bus, side_glass=(Glass(2.9, 3.8, 0.1, 11.4, 8),)))
        with pytest.raises(ValueError, match="leaves the wall"):
            _slab_glass(replace(bus, side_glass=(Glass(2.9, 4.3, 0.7, 11.4, 8),)))

    def test_no_window_stands_in_a_doorway(self) -> None:
        for kind in self.FLAT:
            shape = _shape(kind)
            for start, end in shape.doors_m:
                for run in shape.side_glass:
                    if KERB_SIDE not in run.sides or run.y0_m >= shape.door_head_m:
                        continue
                    # Its surround clear of the door's frame too.
                    margin = SURROUND_M if run.surround is not None else 0.0
                    assert run.end_m + margin <= start or run.start_m - margin >= end, (kind, run)

    def test_the_bus_is_blank_where_its_stairs_climb(self) -> None:
        """Offside, behind the driver's window: no lower-deck glass."""
        bus = _shape("bus")
        lower = [
            run
            for run in bus.side_glass
            if -KERB_SIDE in run.sides and run.y1_m < bus.door_head_m + 0.1
        ]
        assert len(lower) == 2
        cab, saloon = sorted(lower, key=lambda run: run.start_m)
        assert saloon.start_m - cab.end_m > 1.0

    def test_an_end_pane_follows_its_raked_face_and_wraps_the_corners(self) -> None:
        for kind in self.FLAT:
            shape = _shape(kind)
            b = _slab(shape)
            parts = {part.name: part for part in _end_panes(shape)}
            for index, pane in enumerate(shape.end_panes):
                tag = f"pane_{index}_{'rear' if pane.rear else 'front'}"
                out = 1.0 if pane.rear else -1.0
                rake = shape.backlight_rake_deg if pane.rear else shape.windscreen_rake_deg
                end = shape.body_rear_z_m if pane.rear else shape.body_front_z_m
                for x, y, z in parts[tag].positions:
                    assert abs(x) <= b.half_w - b.cut, tag
                    # The face by the shape's own rake, not the builder's `end_z`:
                    # upright to the belt, leaning in by the tangent above it.
                    lean = max(0.0, float(y) - shape.belt_y_m) * math.tan(math.radians(rake))
                    proud = (z - (end - out * lean)) * out
                    assert 0.0 < proud < shape.bumper_m, tag
                assert (f"{tag}_l" in parts) == pane.corners
                if pane.corners:
                    for side_tag in ("l", "r"):
                        wrap = np.abs(parts[f"{tag}_{side_tag}"].positions[:, 0])
                        assert wrap.min() > b.half_w - b.cut and wrap.max() < shape.half_width_m

    def test_the_tram_wears_the_models_plain_green_under_a_dark_roof(
        self, by_name: dict[str, MeshData]
    ) -> None:
        tram = _shape("tram")
        assert tram.band is None and tram.roof != tram.paint
        mesh = by_name["tram"]
        roof = np.all(mesh.colours[:, :3] == np.array(tram.roof, dtype=np.uint8), axis=1)
        assert roof.any()
        assert mesh.positions[roof, 1].min() >= _slab(tram).shoulder_y - 1e-6

    def test_a_glint_lies_in_its_own_window_and_is_glass(
        self, by_name: dict[str, MeshData]
    ) -> None:
        """The user's pick of five glass treatments (2026-11-11): one pale
        streak a side window, proud of the pane, inside it, and marked glass
        so it reflects by day and lights with the saloon at night."""
        assert {shape.kind for shape in SHAPES if shape.glint is not None} == GLINTED
        for kind in GLINTED:
            shape = _shape(kind)
            parts = _slab_glass(shape)
            panes = {part.name: part for part in parts if part.name.startswith("glass_")}
            glints = [part for part in parts if part.name.startswith("glint_")]
            assert glints, kind
            for glint in glints:
                _, run, bay, side = glint.name.split("_")
                pane = panes[f"glass_{run}_{bay}_{side}"]
                for axis in (1, 2):
                    assert glint.positions[:, axis].min() >= pane.positions[:, axis].min() - 1e-6
                    assert glint.positions[:, axis].max() <= pane.positions[:, axis].max() + 1e-6
                assert np.abs(glint.positions[:, 0]).min() > np.abs(pane.positions[:, 0]).max()
                assert np.abs(glint.positions[:, 0]).max() < shape.half_width_m
            mesh = by_name[kind]
            streak = np.all(mesh.colours[:, :3] == np.array(GLINT, dtype=np.uint8), axis=1)
            assert streak.any()
            assert np.all(mesh.uvs[streak, 1] == LIT_CABINS[kind]), kind

    def test_a_run_with_no_room_for_its_windows_is_refused(self) -> None:
        with pytest.raises(ValueError, match="no width"):
            Glass(1.4, 2.2, 1.0, 1.2, 4, pillar_m=0.07)
        with pytest.raises(ValueError, match="top light"):
            Glass(1.4, 1.6, 1.0, 5.0, 4, top_light_m=0.2)

    def test_applied_glass_on_a_lofted_body_is_refused(self) -> None:
        with pytest.raises(ValueError, match="flat-sided"):
            replace(_shape("coach"), glint=GLINT)
        with pytest.raises(ValueError, match="lofted glass"):
            replace(_shape("bus"), blind_rear_share=0.2)
