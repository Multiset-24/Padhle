"""Import the phase 1 modules so a broken dependency fails in CI."""

def test_phase1_modules_import():
    import eye.alarm  # noqa: F401
    import eye.camera  # noqa: F401
    import eye.landmarks  # noqa: F401
    import eye.metrics  # noqa: F401
