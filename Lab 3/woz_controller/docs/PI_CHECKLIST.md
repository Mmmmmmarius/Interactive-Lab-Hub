# Pi on-site acceptance checklist

This checklist is for the user to run beside their Pi after waking. Every result is **Not yet run**. Expected behavior is an acceptance criterion, not proof of a successful hardware test. Mac simulation results do not replace this checklist. Confirm a suitable setting before deliberately testing the microphone and speaker.

Test date: ________  Pi / branch / HEAD: ________  Operator: ________

## 1. Pre-deployment checks and backup

- [ ] **Not yet run**: Confirm the target is the existing `/home/pi/Interactive-Lab-Hub/Lab 3/`. Run `git status --short` at the Pi repository root and review existing changes. Preserve and review any personal writing for A/B/C or other task changes instead of overwriting them with this package. Record: ________
- [ ] **Not yet run**: Make a separate backup of the current Lab 3 files, especially `woz_controller/`, the README, dialogue, scripts and images. Confirm the backup is readable. Backup location: ________
- [ ] **Not yet run**: Check the deployment package against its `.sha256`. If `woz_controller/` already exists, compare it and preserve local changes before merging individual files. Do not overwrite all of Lab 3. Record: ________
- [ ] **Not yet run**: Deploy only this package's `woz_controller/` to `Lab 3/woz_controller/`. Do not replace the Pi's `Lab 3/README.md`, `speech-scripts/`, `voices/`, `models/`, `.venv/` or other course files. Record: ________
- [ ] **Not yet run**: Confirm the old `piscreen.service` is unchanged. Do not stop, disable or replace it. Use the browser page for participant status first. Record: ________

This preparation round did not automatically push, submit to Canvas, start Pi services or message the teaching team. None of those actions is required for on-site technical acceptance.

## 2. Run checks without recording or playback first

Use the Pi's existing Lab 3 virtual environment without creating an environment, installing dependencies or downloading models:

```sh
cd "/home/pi/Interactive-Lab-Hub/Lab 3"
source .venv/bin/activate
python3 woz_controller/check_environment.py
```

- [ ] **Not yet run**: `check_environment.py` returns `ok: true`. Modules, Piper voice/config, the Silero VAD model and `aplay` are present. Missing items or errors: ________
- [ ] **Not yet run**: The reported input is `16000 Hz mono float32`. The voice configuration's sample rate matches the existing speaker path, expected to be 22050 Hz. Record: ________
- [ ] **Not yet run**: The dialogue JSON has `speech_start_timeout_seconds` set to `2.0` and `min_silence_seconds` set to `0.8`. Flower is the default mode. Record: ________

This check only inspects module locations, files and configuration. It does not open audio devices or load speech models, and it does not establish that the Whisper cache, device volume or real recognition works. Record missing dependencies, models or installation and permission requests as blockers. Do not change device security or synchronization settings merely to complete acceptance.

## 3. Choose one on-site entry point

Run only one entry point at a time to avoid microphone contention. Startup alone does not record audio. `say`, `listen`, `morning` and work-scene actions enter the real audio flow.

Console entry point:

```sh
python3 woz_controller/console.py --backend pi --model tiny.en
```

Commands: `status`, `say TEXT`, `listen`, `morning`, `auto on`, `auto off`, `work 0.05`, `work 45`, `remind`, `accept`, `defer`, `pause`, `resume`, `stop`, `reset`, `quit`. `simulate` is only for dry runs and does not replace Pi hardware testing.

Alternatively, start the loopback web interface:

```sh
python3 woz_controller/server.py --backend pi --model tiny.en
```

On the Pi, open `http://127.0.0.1:8765/wizard` and `http://127.0.0.1:8765/participant`. To view them from the Mac, forward the port through the existing authorized SSH connection. For example, if the existing alias is still valid, run on the Mac:

```sh
ssh -N -L 8765:127.0.0.1:8765 cornell-pi-ts
```

Keep the server bound to `127.0.0.1`. Do not expose it publicly or on the LAN, open ports or install a persistent service. If the existing connection or port has changed, check the user's known configuration rather than creating new access permissions.

- [ ] **Not yet run**: The entry point shows `backend=pi`. Console or web status shows Flower, Quiet and no error. The participant page displays status only. Record: ________
- [ ] **Not yet run**: Only one audio process is running. The operator knows where `stop`, Stop now and the exit controls are. Record: ________

## 4. Response windows and complete utterances

Use `auto off` first to check input independently. Before each test, confirm with `status` that `active_action` is empty. `reset` restores `auto on`, so run `auto off` again for manual tests.

Measure from the end of the box's last audible syllable and observe the transition to Listening / `waiting_for_start`. The window decides whether speech **starts** in time. Once it starts, the system captures the whole utterance until about 0.8 seconds of silence. Device latency and roughly one VAD window, typically about 32 ms, limit timing precision. Repeat tests near 2.0 seconds and record deviations. VAD confirmation buffering should not become extra time for accepting a late start.

- [ ] **Not yet run**: Run `say Hello. Take your time.` and remain silent. After playback, Listening returns to Quiet if speech does not start within about two seconds. There is no automatic replay or continuous listening. Record: ________
- [ ] **Not yet run**: Say a short sentence within the window, then remain silent for about 0.8 seconds. The state changes to Thinking. The two-second deadline does not truncate the first word, last word or full sentence. Record transcription errors separately from recording truncation: ________
- [ ] **Not yet run**: Start an utterance of at least ten seconds within the window, speak naturally and finish with silence. Capture continues beyond two seconds, and transcription starts only after the utterance ends. Check the last words without treating every ASR omission as recording truncation. Record: ________
- [ ] **Not yet run**: Test a continuous utterance longer than the old 38-second limit, keeping pauses shorter than 0.8 seconds. Confirm that capture continues until the speaker finishes without the old fixed-duration cutoff. Use `stop` if necessary. Record: ________
- [ ] **Not yet run**: Natural pauses shorter than 0.8 seconds do not immediately end the utterance. Silence longer than 0.8 seconds ends the turn. Actual pause lengths and behavior: ________

For the following three tests, use the same short sentence and repeat each at least three times. A manual stopwatch and listening cannot establish an exact millisecond boundary. Record approximate timings and any instability. Leave unstable boundary behavior as an on-site issue instead of marking it conclusively passed.

| Target speech start | Expected behavior | Result |
| --- | --- | --- |
| About 1.9 seconds | Accept the start, capture the full sentence and let VAD end it. | [ ] Not yet run. Record: ________ |
| About 2.0 seconds | The rule includes a start at exactly 2.0 seconds. Account for VAD and device timing uncertainty on site. | [ ] Not yet run. Record: ________ |
| About 2.1 seconds | The window times out and does not accept the late sentence as this turn's response. | [ ] Not yet run. Record: ________ |

## 5. Repeated turns, morning scene and speaker feedback

- [ ] **Not yet run**: Run `auto on`, then `say Morning.`, and respond for at least three turns. Each preset reply opens a fresh two-second start window. Remain silent after the final turn and confirm a return to Quiet. This version uses preset replies, so semantic quality does not determine whether the audio pipeline passes. Record: ________
- [ ] **Not yet run**: Run `morning` and remain silent after the first self-talk line. Confirm its two-second window, followed by the configured self-talk pause and greeting. The greeting also has a working response window. Record: ________
- [ ] **Not yet run**: Restart the morning scene and respond after its first line. Confirm that the turn is processed fully and the second line does not interrupt the person speaking. Record: ________
- [ ] **Not yet run**: After a `say` action, remain completely silent and watch for the box transcribing its own output or entering a reply loop in a quiet room. Repeat at least three times. Record speaker volume, placement and behavior: ________
- [ ] **Not yet run**: Repeat in the actual desktop and box arrangement, listening for the final syllable, speaker decay and room echo. Recognition should not run during playback, and residual sound afterward should not count as a human response. If it does, record the text and timing, use `stop` and retain it as an unresolved hardware issue. A code-order check does not establish success. Record: ________
- [ ] **Not yet run**: Speak while the box is playing. This must not start recognition or become stale input for the next turn. Speak a new sentence after the next Listening window opens; only the new turn should be processed. Record: ________

## 6. Pause, reset, failures and cancellation

- [ ] **Not yet run**: Use `pause` during playback. Sound stops and the state remains Paused. Repeat during listening: input stops and the unfinished turn is discarded. No new speech or reminder starts while waiting. Record: ________
- [ ] **Not yet run**: Use `resume` to return to Quiet without continuing the old partial recording. Wait for the old worker to finish before starting a fresh turn with `listen` or `say`. Record: ________
- [ ] **Not yet run**: Test a recoverable input failure. Pause and confirm the audio worker has finished, temporarily disconnect the external microphone, then run `listen` and observe whether a device error appears. If automatic input switching prevents reproduction, record it as not reproduced rather than a passed failure path. Reconnect the same microphone, `reset` and test a new turn. Do not change default system audio settings. Record: ________
- [ ] **Not yet run**: Compare ASR for clear and unclear speech. Use `auto off` and web transcript correction or manual `say` as a fallback for recognition errors. If speech is captured but no words are recognized, the error should be displayed and retry should be possible. If that case does not occur, leave it untested rather than moving models or installing dependencies to force it. Record: ________
- [ ] **Not yet run**: Use `stop` during Thinking / `transcribing`. Quiet may appear before `active_action` clears, while the latter still reads `cancelling; wait for audio worker`. Wait for the native Whisper call to finish and `active_action` to clear before sending another action. During cancellation, new actions should return Busy, and the old transcript must not trigger a reply. Waiting time: ________
- [ ] **Not yet run**: Use `reset` to clear errors, the transcript and the previous line, return to Flower / Quiet and restore preset automatic replies. If the old worker is still cancelling, wait until it finishes. A new turn can then run. Record: ________

A native Whisper computation already in progress is not guaranteed to stop immediately. `stop` requests cancellation of its result and subsequent actions. Do not launch repeated processes to bypass Busy, and do not treat Quiet alone as proof that the worker has finished.

## 7. Work timer and silence after stopping

For each work test, let the confirmation line's two-second response window expire naturally. Start timing when the work action completes and `work.running=true`, not when the command is first entered.

- [ ] **Not yet run**: Run `work 0.05`, a three-second compressed test. From `work.running=true`, observe one automatic reminder without web polling or manual `remind`. The reminder also opens a two-second response window. Wait at least ten more seconds and confirm there is no repeated reminder. Record: ________
- [ ] **Not yet run**: Test `accept` and `defer` separately. Accept plays the closing line and opens a response window. Defer closes the current session and returns to Quiet. Both stop the current timer. Record: ________
- [ ] **Not yet run**: Use `pause` after starting a timer. Remaining time freezes and no reminder plays. `resume` continues from the remaining time. Record: ________
- [ ] **Not yet run**: Start a compressed timer and use `stop` before the reminder. Confirm `work.running=false` and no deadline. Wait beyond the old deadline and at least ten additional seconds without another reminder. Also test `stop` during reminder playback: sound stops with no later reminder. Record: ________
- [ ] **Not yet run**: Run `work 45` and work quietly after the confirmation and response window. For the full 45 minutes, there should be no idle chatter, continuous listening or early reminder. One reminder plays at expiry. If the full interval was not observed, leave this item Not yet run and record only the configuration check. Start and expiry: ________
- [ ] **Not yet run**: Finally, use `stop`, confirm the worker has finished, then `quit` or press Ctrl+C. Confirm there is no residual playback, reminder or newly installed persistent service. Record: ________

## 8. Reserved interfaces and evidence boundaries

- [ ] **Not yet run**: Status still shows `mode: flower`, Muse `available: false` and `wake_interface: reserved`. Muse only reserves a future independent wake-word interface in this version. It cannot actually wake, pair or send user data. Do not install Muse or a network service. Record: ________
- [ ] **Not yet run**: The user checks whether the teaching team was previously notified of AI technical assistance. Local materials document Codex use and purpose, but no sending, receipt or acknowledgment evidence was found. No notification was sent or claimed on the user's behalf. Evidence or pending confirmation: ________
- [ ] **Not yet run**: Record actual commands, parameters, passed, failed and unrun items, and hardware issues. Participant audio is not saved by default, and session state remains in process memory. Retain on-site records as needed without marking unrun items as passed. Record location: ________

Check an item only after it has actually been executed and meets the expected behavior. Retain explanations for failures and cases that could not be reproduced. This is a technical acceptance checklist, not proof that the assignment is complete.
