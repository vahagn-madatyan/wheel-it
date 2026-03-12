import pytest
import shutil
import tempfile
from pathlib import Path


@pytest.fixture
def tmp_config_dir():
    """Creates a temp directory with presets/ subdirectory, yields the path, cleans up after."""
    tmpdir = Path(tempfile.mkdtemp())
    presets_dir = tmpdir / "presets"
    presets_dir.mkdir()
    yield tmpdir
    shutil.rmtree(tmpdir)


@pytest.fixture
def sample_screener_yaml():
    """Returns a valid screener.yaml string content with preset: moderate and one override."""
    return (
        "preset: moderate\n"
        "fundamentals:\n"
        "  market_cap_min: 5000000000\n"
    )
