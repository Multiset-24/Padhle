# Project Eye

Project Eye is a local macOS alarm for study sessions. It watches the webcam, measures how closed your eyes are, and beeps when they stay closed. Everything runs on your machine.

This repository is [Padhle](https://github.com/Multiset-24/Padhle). Phase 1 is the minimum version: a preview window with live eye aspect ratio (EAR) and frames per second, plus a beep after a long closure. The full design is in [PLAN.md](PLAN.md).

## What this version does

- Captures the webcam on a background thread at 640×480.
- Finds the face with MediaPipe Face Landmarker (Tasks API).
- Computes EAR from the plan's landmark indices and averages both eyes.
- Shows EAR, FPS, and a status line in an OpenCV window.
- Beeps when EAR stays under the closed threshold for longer than 2 seconds.
- Shows `no face` or `camera unavailable` instead of crashing. Press `q` to quit.

The starting threshold is 0.2, in `config.yaml`. Open eyes are usually about 0.25–0.35. Change `ear.closed_threshold` and `ear.closed_seconds` there to tune it.

## Setup

Python 3.11 or newer. On an Apple Silicon Mac, install into a normal virtual environment. `opencv-python`, `mediapipe`, and `pygame` publish macOS arm64 wheels, and the landmarker runs on CPU.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Download the Face Landmarker model (about 3.6 MB). `python main.py` also downloads it on first launch if this file is missing.

```bash
python scripts/download_model.py
```

The file is saved to `models/face_landmarker.task` and is gitignored. The download URL is the official model linked from the [Face Landmarker Python guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python):

`https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task`

## Run

```bash
python main.py
```

Sit with your face in frame and the light in front of you. The window title is **Project Eye**.

| On screen | Meaning |
| --- | --- |
| `eyes open` / `eyes closed` | EAR is above or below the threshold |
| `beep` | Eyes have stayed closed longer than `ear.closed_seconds` |
| `no face` | The landmarker does not see a face |
| `camera unavailable` | The webcam could not be opened or read. The app retries every 5 seconds |
| `opening camera` | The first open attempt is still in progress |

Press `q` to quit.

### Camera access on macOS

The first launch asks the app that started Python (Terminal, iTerm, Cursor, or another IDE) for permission to use the camera. Allow it.

If the preview stays on `camera unavailable`, or the prompt never appears:

1. Open **System Settings > Privacy & Security > Camera**.
2. Turn Camera on for Terminal, iTerm, or the IDE that runs `python main.py`.
3. Quit that app completely and run Project Eye again.

The capture path uses OpenCV's AVFoundation backend (`cv2.CAP_AVFOUNDATION`) on macOS, then the default backend if that open fails. A camera already in use by a video call shows `camera unavailable` until it is free.

## Privacy

Processing stays on this machine. Frames are held in memory for the preview and are not written to disk or uploaded. The only network request is the one-time download of the Face Landmarker model.

## Tests

```bash
python -m pytest
```

The tests build eye shapes by hand and drive the closure timer with a fake clock. They do not open a webcam, play audio, or download the model.

## Phase checklist

- [x] Set up the repo and Python environment
- [x] Phase 1: minimum version
- [ ] Phase 2: calibration and smoothing
- [ ] Phase 3: more signals
- [ ] Phase 4: alarm levels
- [ ] Phase 5: tuning on recorded sessions
- [ ] Phase 6: polish and packaging

Phase 1 is done when closing your eyes for 2 seconds beeps every time. Later phases add personal calibration, more drowsiness signals, the four-level alarm, and the tray app. They are described in [PLAN.md](PLAN.md) and are not in this version.
