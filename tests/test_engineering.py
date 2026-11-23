import random
from fractions import Fraction
from math import fsum

import pytest

from hullguard.calculations import assembly_mass_kg, mass_kg, volume_m3
from hullguard.comparison import compare_models
from hullguard.geometry import read_obj, write_obj
from hullguard.models import Component, ComponentId, ModelError, load_model, parse_model


def test_hand_calculated_bottom_masses(baseline, fixture_dir):
    changed = load_model(fixture_dir / "thickness_changed.json")
    parts = [
        next(part for part in model.components if part.id == "P-01")
        for model in (baseline, changed)
    ]
    assert volume_m3(parts[0]) == pytest.approx(0.012)
    assert volume_m3(parts[1]) == pytest.approx(0.016)
    assert mass_kg(parts[0]) == pytest.approx(94.2)
    assert mass_kg(parts[1]) == pytest.approx(125.6)
    assert mass_kg(parts[1]) - mass_kg(parts[0]) == pytest.approx(31.4)


def test_independent_assembly_volume_and_mass(baseline):
    # Integer cubic millimetres computed from the engineering layout, grouped by paired parts.
    bottom = 12_000_000
    side_pair = 10_320_000
    bulkhead = 3_398_720
    front_pair = 1_196_800
    rear_pair = 970_496
    reference_kg = (bottom + side_pair + bulkhead + front_pair + rear_pair) * Fraction(
        157, 20_000_000
    )
    assert reference_kg == Fraction("218.9052256")
    assert assembly_mass_kg(baseline) == pytest.approx(float(reference_kg), abs=1e-9)


def test_mass_scales_linearly_in_each_axis_and_ignores_position():
    rng = random.Random(7850)
    for _ in range(40):
        size = tuple(rng.randint(1, 800) for _ in range(3))
        origin = tuple(rng.randint(-600, 600) for _ in range(3))
        axis = rng.randrange(3)
        factor = rng.randint(2, 9)
        scaled = tuple(x * factor if i == axis else x for i, x in enumerate(size))
        source = Component(ComponentId("S-01"), "stiffener", "steel-example", (0, 0, 0), size)
        candidate = Component(source.id, source.kind, source.material, origin, scaled)
        assert mass_kg(candidate) == pytest.approx(factor * mass_kg(source), rel=1e-12)


def test_obj_encloses_expected_volume_independently(baseline):
    headers, meshes = read_obj(write_obj(baseline))
    assert headers == {"revision": baseline.revision, "units": "mm"}
    assert set(meshes) == {part.id for part in baseline.components}

    # Signed tetrahedron determinant for every exported triangle, with vertices in mm.
    def determinant(a, b, c):
        return (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            + a[1] * (b[2] * c[0] - b[0] * c[2])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        )

    for component in baseline.components:
        mesh = meshes[component.id]
        assert mesh.bounds == (component.origin_mm, component.maximum_mm)
        assert mesh.is_closed_outward_box()
        volume = fsum(
            determinant(*(mesh.vertices[index] for index in face)) / 6 for face in mesh.faces
        )
        x, y, z = component.size_mm
        assert volume == pytest.approx(x * y * z, abs=1e-6)


def test_thickness_revision_affects_only_bottom(baseline, fixture_dir):
    revised = load_model(fixture_dir / "thickness_changed.json")
    result = compare_models(baseline, revised)
    assert revised.revision != baseline.revision
    assert result["delta_mass_kg"] == pytest.approx(31.4)
    assert not result["added"] and not result["removed"]
    (change,) = result["modified"]
    assert change["id"] == "P-01"
    assert change["delta_dimensions_mm"] == [0, 0, 2]
    assert change["delta_position_mm"] == [0, 0, -2]
    assert {"model.obj", "manifest.json", "bom.csv", "drawing.svg"} <= set(
        result["affected_artifacts"]
    )


def test_stiffener_revision_reports_identity_and_position(baseline, fixture_dir):
    revised = load_model(fixture_dir / "stiffener_changed.json")
    result = compare_models(baseline, revised)
    assert [p["id"] for p in result["added"]] == ["S-05"]
    assert [p["id"] for p in result["removed"]] == ["S-04"]
    (change,) = result["modified"]
    assert change["id"] == "S-01"
    assert change["delta_position_mm"] == [0, 30, 0]
    assert change["delta_dimensions_mm"] == [0, 2, 0]
    assert result["delta_mass_kg"] == pytest.approx(1.17436)


def test_same_revision_has_no_artifact_impact(baseline):
    result = compare_models(baseline, baseline)
    assert (result["modified"], result["delta_mass_kg"], result["affected_artifacts"]) == (
        [],
        0,
        (),
    )


def test_comparison_rejects_different_projects(baseline, baseline_raw):
    baseline_raw["project"] = "Different bay"
    with pytest.raises(ModelError, match="same project"):
        compare_models(baseline, parse_model(baseline_raw))
