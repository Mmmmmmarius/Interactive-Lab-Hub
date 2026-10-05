# Daily ornament iteration: 2026-10-04

The student approved this direction before implementation: an interactive decoration, not a helpful assistant. The existing 2.0-second speech-start window and 0.8-second silence endpoint are retained. Speech recognition supplies the turn boundary/transcript, but does not choose a semantically matched answer.

## Daily sequence

1. If already running at 10:30 in America/New_York, play the morning scene once. Responding to its first line enters the reply loop rather than overlapping the second greeting.
2. After a completed interaction, wait a randomly selected 1,800–5,400 seconds, then choose a self-talk preset. On a recognized reply, choose a response preset and open another response window. No response returns the box to Quiet.
3. A spontaneous start must occur before 20:00. If a sampled time reaches/exceeds 20:00, the next automatic event is the following morning. An ongoing conversation can finish after 20:00. Manual preview remains possible at any hour.
4. Pause suppresses automatic events; Resume samples a fresh wait. Stop disables the daily schedule until explicitly enabled or Reset. Reset restores configured defaults. The program’s configured default is enabled; restarting the process restores that default too.

A startup after 10:30 schedules a fresh random daytime wait, never an immediate morning catch-up. A morning that occurs while another conversation is active or the controller is paused/error-blocked is skipped. Normal scheduler jitter up to 60 seconds is tolerated; missed events after a longer computer sleep/jump are discarded and replanned. A backward wall-clock change does not replay the morning. New York daylight saving time comes from IANA timezone data, independently of the host timezone.

Only one process should run. The schedule is in process memory: it does not install an OS task, service or wakeup automation, persist deadlines across restarts, or wake a powered-off Pi. Keep the application and Pi running for the intended day-long behavior. An error blocks new automatic audio until the operator recovers it. Next-event displays are planned times, subject to busy/error/paused conditions.

## Presets and controls

`talking-box-dialogue.json` contains 16 original self-talk lines and 24 replies. Selection excludes the last line in the same pool, but is otherwise random. Examples:

- Self-talk: “I considered being useful. Briefly. It passed.”
- Self-talk: “Some people have a rich inner life. I have excellent corners.”
- Reply: “Look at us having a conversation. The lamp must be furious.”
- Reply: “You brought words. I brought presence. Fair exchange.”

The wizard page shows daily enable/disable, next event with New York date/time, a manual self-talk trigger and random-reply mode. Legacy work controls are collapsed and manual-only. Console `chatter` and `schedule on/off` share the same API dispatch. The participant display remains focused on turn state.

## Verification

Windows Python 3.13.5: **93 tests passed; 0 failures, errors or skips**. The 70 baseline methods remain, with the former constant-reply assertion updated to verify pool membership and non-repetition and HTML/JS source reads made explicitly UTF-8. Twenty-three new tests cover the daily schedule, seeded interval variation, exact 30/90-minute bounds, morning/closing boundaries, no catch-up, midnight, DST, backward clock changes, cancellation, interruption prevention, post-20:00 completion, API/console toggles, preset validation and background triggering without HTTP polling.

Evidence: [test log](validation/daily-unittest.log), [summary](validation/daily-unittest.json), [browser state](validation/daily-browser-dom.txt), [controller screenshot](images/daily-ornament.png). Browser checks observed a random self-talk/reply exchange, next morning at 10:30 EDT, Pause/Resume, Stop disabling the checkbox and schedule, explicit re-enable and Reset. The legacy work panel was initially collapsed. Browser warning/error log query returned no entries. The silent test server was stopped and its port was no longer listening.

The automatic wall-clock scenarios use a virtual clock, not a real all-day wait. The console and HTTP/browser run real local processes with only dry-run audio. No real microphone, speaker, model or Pi was used. The new code has not been deployed to the Pi; prior 70-test evidence remains separately preserved.

## Pi acceptance, all pending

- [ ] Verify IANA New York timezone data, existing models, microphone and speaker before running the day-long mode.
- [ ] Start before 10:30 and observe one morning scene; verify there is no second morning after Reset/restart later that day.
- [ ] Observe actual 30–90 minute waits, measured from the end of the previous interaction, and sensible variety in both pools.
- [ ] Confirm a prompt response starts capture, the complete sentence survives the two-second onset window, and pauses/room echo do not cause unwanted replies.
- [ ] Confirm ongoing conversation finishes after 20:00 while new spontaneous chatter stops.
- [ ] Verify Pause/Resume, Stop remaining off, explicit re-enable, and safe recovery from audio failure.
- [ ] Collect real observations from at least two participants and use the student’s Part 1 records for the course reflection. Do not use dry-run transcripts as participant data.

The old PI_CHECKLIST is retained as historical baseline coverage; its work-timer section now applies only to the optional manual demo. This checklist adds the current daily ornament requirements. No hardware item has been marked complete.
