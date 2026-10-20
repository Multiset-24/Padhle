#!/usr/bin/env python3
"""Download the MediaPipe Face Landmarker model if it is not already present."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eye.landmarks import ensure_model  # noqa: E402


def main() -> int:
    config_path = ROOT / "config.yaml"
    with config_path.open(encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    destination = ROOT / config["model"]["path"]
    url = config["model"]["url"]
    if destination.is_file() and destination.stat().st_size > 0:
        print(f"Model already present at {destination}")
        return 0
    print(f"Downloading {url}")
    try:
        path = ensure_model(destination, url)
    except (OSError, RuntimeError) as exc:
        print(f"Download failed: {exc}", file=sys.stderr)
        return 1
    print(f"Saved {path} ({path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
