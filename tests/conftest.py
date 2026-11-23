import json
from pathlib import Path

import pytest

from hullguard.comparison import create_bundle
from hullguard.models import load_model

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


@pytest.fixture
def fixture_dir():
    return FIXTURES


@pytest.fixture
def baseline_raw():
    return json.loads((FIXTURES / "baseline.json").read_text(encoding="utf-8"))


@pytest.fixture
def baseline():
    return load_model(FIXTURES / "baseline.json")


@pytest.fixture
def bundle(baseline, tmp_path):
    output = tmp_path / "bundle"
    assert create_bundle(baseline, output)["status"] == "PASS"
    return output
