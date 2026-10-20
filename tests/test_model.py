"""Model download should not run again when the file is already on disk."""

from eye.landmarks import ensure_model


def test_ensure_model_keeps_an_existing_file(tmp_path):
    destination = tmp_path / "face_landmarker.task"
    destination.write_bytes(b"already-here")
    result = ensure_model(destination, "https://example.invalid/should-not-be-fetched")
    assert result == destination
    assert result.read_bytes() == b"already-here"
