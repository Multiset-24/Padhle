"""Phase 1 defaults live in config.yaml."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_phase1_defaults():
    with (ROOT / "config.yaml").open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    assert config["camera"]["width"] == 640
    assert config["camera"]["height"] == 480
    assert config["ear"]["closed_threshold"] == 0.2
    assert config["ear"]["closed_seconds"] == 2.0
    assert config["model"]["url"].endswith("face_landmarker.task")
