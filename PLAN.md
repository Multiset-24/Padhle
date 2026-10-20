# Project Eye — Drowsiness Alarm Plan

## Overview

Project Eye is a local desktop app that watches you through the webcam during study sessions and plays an escalating alarm the moment you start dozing off. Everything runs on your own machine; no video is stored or sent anywhere.

**Problem:** during long study sessions, microsleeps and nodding off happen without you noticing, and a fixed timer can't tell when you are actually drowsy.

**Success criteria for v1:**

- Detects eyes closed for 1.5 s or longer within 0.5 s, at least 95% of the time in normal desk lighting
- Fewer than 1 false alarm per hour while reading a book or notes on the desk
- Runs at 15 FPS or more on a typical laptop CPU, using under 25% of the CPU
- Calibration takes under 30 s at the start of a session

## What happens when you get sleepy

Your pattern of eyes getting heavy that a sudden shock clears is ordinary sleepiness during low-stimulation work, briefly overridden by a startle response. The shock wakes you, but it doesn't remove the underlying sleepiness, which is why it comes back.

**Why it builds up while studying:**

- **Sleep pressure:** a chemical called adenosine builds up the longer you're awake and pushes you toward sleep. Short sleep the night before makes it stronger.
- **Low stimulation:** reading or watching lectures while sitting still gives your brain little input, so the drive to sleep wins. This is called the vigilance decrement: alertness falls steadily during long, monotonous tasks, often after 30–60 minutes.
- **Time of day:** alertness naturally dips in the early afternoon (about 1–4 pm) and late at night.

**It happens in stages,** and each stage shows up on camera:

1. **Heavy eyes:** blinks get slower and longer, you yawn, and your eyelids sit lower than usual.
2. **Drowsy:** your eyes close for a second or more, and your head starts to drop.
3. **Microsleep:** your eyes stay closed for several seconds and you lose track of what you were reading.

**Why a sudden shock works:** a surprise triggers a startle response. Your brain releases noradrenaline and adrenaline, your heart rate jumps, and you're fully alert within seconds. The surge fades within minutes, though, and the sleep pressure is still there, so drowsiness returns unless you do something that keeps you stimulated.

**What this means for Project Eye:**

- **Catch stage 1, not just stage 3.** Detecting heavy eyes early lets a mild nudge work before you lose focus.
- **Make the alarm a real surprise.** Sudden, full-volume and unpredictable sounds trigger the startle response; a predictable beep stops working after a few days.
- **Follow the shock with action.** Standing up, moving or answering a question keeps you alert much longer than a sound alone.
- **Watch closely after an alarm.** The next 5–10 minutes are when you're most likely to drift off again.
- **Learn your pattern.** If you usually get drowsy about 40 minutes in, the app can suggest a break just before then.
- **Treat repeated episodes as real tiredness.** Several alarms in a short time mean you need a short nap or a proper break, not more alarms.

If you get this sleepy most days even after 7–9 hours of sleep, it's worth mentioning to a doctor, since excessive daytime sleepiness can have medical causes.

## Tech stack

Build it in Python with MediaPipe for face tracking. A desktop app keeps tracking while you switch windows, which a browser tab doesn't do reliably.

| Part | Tool | Why |
| --- | --- | --- |
| Language | Python 3.11+ | Best ecosystem for webcam and computer vision |
| Camera input | OpenCV (`opencv-python`) | Reliable webcam capture on Windows, macOS and Linux |
| Face and eye tracking | MediaPipe Face Landmarker | 478 face points including irises, plus blendshape scores such as `eyeBlinkLeft`, `eyeBlinkRight` and `jawOpen`; runs on CPU |
| Head pose | MediaPipe transformation matrix, or OpenCV `solvePnP` | Head pitch, to detect nodding and looking down |
| Sound | `pygame.mixer` | Looping playback with volume control for escalating alarms |
| Settings | `config.yaml` | Tune thresholds without code changes |
| UI | OpenCV preview window first, PySide6 tray app later | The preview helps while tuning; the tray app suits daily use |
| Packaging | PyInstaller | Single executable you can start before studying |

**Hardware:** a built-in laptop webcam is enough to start. A USB webcam at eye level is better. Get an IR webcam if you often study in dim light.

## Detection approach

Combine six signals so that a single blink or glance down never triggers an alarm on its own.

**Eye Aspect Ratio (EAR)** is the main signal: eye height divided by eye width, computed from 6 landmarks per eye.

```latex
\text{EAR} = \frac{\lVert p_2 - p_6 \rVert + \lVert p_3 - p_5 \rVert}{2\,\lVert p_1 - p_4 \rVert}
```

MediaPipe landmark indices in p1–p6 order: left eye 33, 160, 158, 133, 153, 144; right eye 362, 385, 387, 263, 373, 380. Open eyes usually measure 0.25–0.35 and closed eyes below 0.15. Average both eyes, and use the `eyeBlink` blendshape score as a second check.

| Signal | Stage | How it's measured | Starting threshold |
| --- | --- | --- | --- |
| Heavy eyes | 1 | Average eye openness over the last 2 min compared with your calibrated open baseline | Below 85% of baseline |
| Slow blinks | 1 | Average blink duration over the last 2 min | Over 0.4 s, or 50% longer than at session start |
| Yawning | 1 | `jawOpen` blendshape, or mouth aspect ratio | Over 0.6 for more than 2 s |
| PERCLOS | 1–2 | Share of the last 60 s with eyes at least 80% closed | Over 10% early warning, over 15% drowsy |
| Long eye closure | 2–3 | Consecutive time with EAR under your calibrated threshold | Over 1.5 s drowsy, over 3 s microsleep |
| Head nodding | 2–3 | Head pitch falls quickly, then snaps back | Pitch change over 15° in under 1 s |
| Face lost | 3 | No face detected | Over 5 s while a session is running |

The stage column matches the three stages above. Stage 1 signals are trends over minutes, so they catch heavy eyes before any single long closure happens. These thresholds are starting points. Phase 5 tunes them on recordings of your own sessions.

## Tracking accuracy

Accuracy depends mostly on per-person calibration and on handling the looking-down case. Lighting and camera position come next.

**Calibration at the start of each session (about 25 s):**

1. Look at the screen with your eyes open for 8 s to record your open-eye baseline.
2. Close your eyes for 3 s to record your closed-eye baseline.
3. Look down at your book or notes for 8 s to record the reading baseline and head pitch.
4. Set the closed threshold halfway between the open and closed averages, separately for screen and reading poses.

**Looking down at a book is the biggest source of false alarms.** When you read, your eyelids lower and EAR drops even though you're awake. To handle it:

- Use head pitch to decide whether the screen or the reading baseline applies.
- When the head is tilted down, require a longer closure (2.5 s instead of 1.5 s) before alarming.
- Use the iris landmarks: if the iris is still visible, the eye is open.

**Other accuracy measures:**

- **Smoothing:** apply a moving average over 3–5 frames so single noisy frames don't count.
- **Lighting:** light your face from the front and avoid a window behind you. Warn the user if average face brightness is too low.
- **Camera:** place it near eye level with your whole face in frame, 50–80 cm away.
- **Glasses:** tilt the lamp or screen to reduce glare, and rely more on the blendshape score, which copes better with glare.
- **Performance:** process frames at 640×480 and run capture in its own thread to keep 15 FPS or more.
- **Drift:** slowly update the open-eye baseline during clearly alert periods, because eyes get tired over a long session.

## Alarm levels

The alarm gets louder in four levels. Level 3 keeps sounding until you prove you're awake.

| Level | Trigger | Response | Clears when |
| --- | --- | --- | --- |
| 0 Alert | Normal readings | Silent | — |
| 1 Heavy eyes | Heavy eyes, slow blinks, a yawn, or PERCLOS over 10% | Soft chime plus an on-screen prompt: stand up, stretch, drink water | Automatically after 2 min of normal readings |
| 2 Drowsy | Eyes closed over 1.5 s, or a head nod | Sudden loud sound at full volume, chosen at random | Eyes open for 2 s straight |
| 3 Asleep | Eyes closed over 3 s, or face lost over 5 s | Startle alarm on loop | You stand up and step out of frame for 5 s, or solve a quick math problem |

**Make it a real surprise, like someone interrupting you:**

- Start levels 2 and 3 at full volume instantly, with no fade-in. A sudden onset is what triggers the startle response.
- Pick a random sound from a pool of 8–10 (voice shouts, a clap, a door knock, a phone ring, an alarm buzzer) so your brain can't predict it.
- Add a random delay of 0–0.5 s so the timing isn't predictable either.
- Optionally flash the screen white or bring the app to the front at level 3.
- Set the app volume independently of the system volume, with a minimum for level 3.

**After the alarm, keep you awake:**

- The level 3 dismiss requires action (standing up or solving a problem), because movement keeps you alert longer than a sound alone.
- For 10 minutes after any level 2 or 3 alarm, enter a watch period: closure thresholds drop by 30%, and level 1 prompts fire sooner.
- During the watch period, show a short active task every few minutes, such as answering a question about what you just read.

**Break suggestion:** if level 2 or higher fires 3 times within 15 minutes, show a message suggesting a 10–20 minute break or short nap. An alarm wakes you briefly, but it doesn't fix being genuinely tired.

**Learn your pattern:** log when each episode starts (minutes into the session and time of day). After 5 or more sessions, if drowsiness usually begins around the same point, such as 40 minutes in, prompt a 3–5 minute active break a few minutes before it.

## Architecture

A single loop processes each frame through four stages. Only the state machine decides when to sound the alarm, so all the timing rules live in one place.

Pipeline: camera → landmarks → metrics → state machine → alarm, with calibration feeding per-user limits into the state machine and the state machine also driving the session logger.

```text
eye/
├── main.py              # main loop: camera → landmarks → metrics → state → alarm
├── config.yaml          # thresholds, sound files, camera index
├── eye/
│   ├── camera.py        # threaded webcam capture
│   ├── landmarks.py     # MediaPipe Face Landmarker wrapper
│   ├── metrics.py       # EAR, PERCLOS, head pitch, yawn, face lost
│   ├── calibration.py   # screen and reading baselines
│   ├── state.py         # alarm level 0–3 and timers
│   ├── alarm.py         # pygame sounds, rotation, dismiss challenge
│   └── logger.py        # per-session CSV
├── sounds/
├── logs/
└── tests/
    ├── test_metrics.py
    ├── test_state.py
    └── clips/           # labelled recordings for replay tests
```

## Milestones

Build it in six phases. Each phase ends with something you can use in a real study session.

1. **Minimum version (1 evening):** webcam → MediaPipe → EAR shown on screen → beep when eyes are closed over 2 s.
   - Done when: closing your eyes for 2 s beeps every time.
2. **Calibration and smoothing (1–2 days):** the 25 s calibration flow, personal thresholds, frame smoothing.
   - Done when: normal blinks never trigger it over a 30-minute session.
3. **More signals (2–3 days):** early heavy-eye signals (eye openness trend, slow blinks, yawning), PERCLOS, head pitch and nodding, face-lost check, reading-pose handling.
   - Done when: reading a book for 30 minutes causes at most 1 false alarm.
4. **Alarm levels (1–2 days):** the four-level state machine, sudden randomized startle sounds, action-based dismiss, the 10-minute watch period after an alarm, break suggestion.
5. **Tuning (ongoing):** record 3–5 real study sessions, replay them through the pipeline, adjust thresholds in `config.yaml`.
6. **Polish (2–3 days):** system-tray app, start/pause hotkey, session stats (drowsy episodes and when they happened), learned drowsiness onset with pre-emptive break prompts, PyInstaller build.

- [ ] Set up the repo and Python environment
- [ ] Phase 1: minimum version
- [ ] Phase 2: calibration and smoothing
- [ ] Phase 3: more signals
- [ ] Phase 4: alarm levels
- [ ] Phase 5: tuning on recorded sessions
- [ ] Phase 6: polish and packaging

## Testing, privacy and risks

**Testing:**

- Unit-test `metrics.py` with hand-made landmark points: known open and closed eye shapes must give the expected EAR.
- Unit-test the state machine with scripted EAR sequences: a 0.3 s blink stays at level 0; a 3.5 s closure reaches level 3.
- Record short labelled clips (awake, reading, blinking, eyes closed, nodding, yawning) and replay them in CI to catch regressions.
- Track two numbers per tuning round: missed dozes and false alarms per hour.

**Privacy:** all processing is local. Frames are never saved unless you turn on recording for tuning. Logs keep only numbers (time, EAR, level).

**Risks:**

| Risk | Mitigation |
| --- | --- |
| False alarms while reading | Reading-pose baseline, longer closure threshold when head is down, iris visibility check |
| Poor tracking in dim light | Brightness warning; IR webcam |
| Getting used to the alarm | Sound rotation, dismiss challenge |
| Camera in use by another app (video call) | Show a clear "camera unavailable" status and retry every 5 s |
| High CPU on older laptops | Lower resolution, skip every other frame, cap at 15 FPS |

**Open questions (answered):**

- Which OS do you study on? macOS.
- Do you want session stats and graphs, or only the alarm? Yes, graphs should be there.
- Should it later work on a phone propped on the desk? Undecided.
