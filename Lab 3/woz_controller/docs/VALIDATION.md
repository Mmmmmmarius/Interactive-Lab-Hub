# Technical validation checkpoint: 2026-10-04

The source archive was supplied by the user and matched SHA-256 `d42088bf89df7046ef946551d47953250308548aa55397b0bc0980364580d080`. All 35 ZIP entries passed CRC and all 34 original manifest entries matched their hashes and sizes.

On Windows with Python 3.13.5:

- The initial compatible subset passed 63/63, including the three real loopback HTTP tests previously skipped on Mac.
- After adapting the POSIX test doubles, the complete suite passed **70/70, no failures, errors, or skips**. [Log](validation/unittest-windows.log), [summary](validation/unittest-windows.json).
- Ten Python files compiled successfully.
- A real dry-run console process accepted manual speech/listening, timer, pause/resume, stop/reset and quit, then exited with code 0.
- Browser checks covered wizard/participant rendering, pause/resume, transcript correction, visible empty-reply rejection, reset, default and queued simulated transcripts, a three-second reminder, stopping the timer, and participant Paused-state synchronization.
- The test server used only 127.0.0.1 and was stopped afterwards. A favicon request returned 404; controller actions worked. Captured browser warning/error queries were empty.

Only SpeechPipelineTests needed a Windows compatibility change: the test fixture replaces the audio module's local os/signal references with POSIX doubles and restores them after each test. Existing assertions remain. No real child process is signalled by these tests. This validates mocked Pi pipeline logic, not real Windows audio support. Production source and dialogue were copied unchanged from the Windows-verified package; this repository README is a portable replacement for machine-specific handoff notes.

The tests cover simulated onset boundaries, long utterances, end-of-turn silence, multiple turns, error recovery, cancellation, timer behavior and protocol validation. They do not establish Pi device availability, acoustic echo behavior, exact physical onset timing, model quality, participant experience, or a full 45-minute run. All 39 original [Pi checklist](PI_CHECKLIST.md) items remain pending; screenshots are simulation evidence only.
