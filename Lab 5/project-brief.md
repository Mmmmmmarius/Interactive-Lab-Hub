# Project brief: INFO5345 Lab 5 Touch grass score

| Deliverable | Task | Owner | Template version | Status | Constraints confirmed |
| --- | --- | --- | --- | --- | --- |
| Local Lab 5 documentation, Pi application and LAN UI | T088 | Codex | 1 | Implementing the requirements confirmed in this conversation | 2026-11-01 |

## Goal and audience

Build Marius's course project around daytime sampling, a bedtime button press, overnight Qwen analysis and feedback through a LAN page after waking. The documentation should let the instructor assess the interaction and its limitations through actual records.

## Confirmed constraints

- Marius proposed taking one photograph every five minutes during the day and processing the batch at night.
- Start at 08:00 New York time every day. A Mini PiTFT button ends that day's capture and starts processing.
- Qwen estimates desk time and produces a Touch grass score from 0 to 100. More time at the desk means a higher score.
- YOLO handles image detection. Python handles capture, scheduling, detection counts and validation. It does not generate or rewrite Qwen's duration or score. Failed validation may trigger another Qwen attempt, with every original response retained.
- The LAN UI displays status and results. Preserve the instructor's original scripts.
- On November 2, Marius approved the grass-pet visual direction: five score expressions, six operating states and English meme copy, deployed to the Pi with new screenshots in the README. Pet remarks come from frontend copy. The original Qwen results and simulation labels remain visible.
- On November 1, Marius separately approved the express demo: collect real data for 15 minutes, map it to a simulated day and label it clearly. Store it separately from normal records. It cannot replace a full-day test. The provisional simulated period is 08:00–20:00.
- Record AI assistance according to the course configuration. Marius supplies his own ideas, original storyboards, actual feedback and personal reflection.
- The saved Canvas deadline is November 1 at 23:59 New York time. Any extension was not rechecked in this round.

## Acceptance

- [x] The LAN page is readable at desktop and narrow widths and does not invent a score when no data is available.
- [x] The approved grass-pet UI is deployed to the Pi. The current report, clickable copy, history selection and desktop and narrow screenshots have been checked. Original results are unchanged.
- [x] Software checks cover the daily 08:00 start and batch assignment across midnight. The application does not backfill photographs that were never captured.
- [x] Software checks cover debounce, held buttons and duplicate triggers. Physical buttons are verified separately.
- [x] Original photographs, detection records and Qwen responses are traceable.
- [x] Invalid output fields, counts, arithmetic or ranges preserve the original response and trigger a retry. Persistent failure is marked for review instead of being recalculated by Python.
- [x] Two physical button presses, 15 minutes of capture, batch processing and the web result have been executed and saved.
- [ ] Obtain a close-up or user confirmation of the specific TFT screen transitions.
- [x] Reanalysis of the same second-run photographs with improved input produced 552 simulated minutes and a score of 100 from Qwen. The original answer, validation and page agree. Earlier errors are retained.
- [ ] Improve detection further. The second run detected a person in 23 photographs but missed five others with a visible person.
- [ ] Record a full day of sampling followed by overnight processing. Keep short tests separately labeled.

## Current scope

Implement the service, button input and LAN page, run short checks and document operation. Normal capture begins at the first 08:00 after deployment. Storyboard images, peer feedback, personal reflection and a complete day of data remain to be completed.

## Change history

| Date | Change | Basis |
| --- | --- | --- |
| 2026-11-01 | Confirmed the 08:00 start, button-triggered stop, 0–100 score and LAN UI. | Marius confirmed each requirement in this conversation. |
| 2026-11-01 | Added a 15-minute compressed-day demo, preserving real timestamps and clearly labeling simulated results. | Marius requested an express demo and chose to map it to a simulated day. |
| 2026-11-01 | Reused the second-run photographs, provided structured detection counts, and added arithmetic validation that rejects rather than rewrites answers, with bounded retries. Reopened YOLO after updating the README. | Marius explicitly requested improved Qwen input and validation while keeping duration and score calculation in Qwen. |
| 2026-11-02 | Approved the grass-pet UI and English copy, implemented the displayed states and deployed them. | Marius approved the proposal and requested Pi deployment and updated README screenshots. |
