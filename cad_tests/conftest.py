"""Optional integration test configuration."""

from pathlib import Path

import pytest

from scripts.freecad import resolve_command


def pytest_addoption(parser):
    parser.addoption("--freecad", help="FreeCAD console executable")
    parser.addoption("--cad-evidence", type=Path, help="Directory for round-trip observations")


@pytest.fixture(scope="session")
def freecad(request):
    path = request.config.getoption("--freecad")
    if not path:
        pytest.fail("Provide --freecad pointing to a real FreeCAD console", pytrace=False)
    return resolve_command(path)


@pytest.fixture(scope="session")
def evidence_directory(request):
    folder = request.config.getoption("--cad-evidence")
    if folder:
        folder.mkdir(parents=True, exist_ok=True)
    return folder
