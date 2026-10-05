# Lab 3 Part 2: requirement review and proposed next work

Reviewed 2026-10-04 against the [official Fall2026 Lab 3 instructions](https://github.com/IRL-CT/Interactive-Lab-Hub/blob/Fall2026/Lab%203/README.md#lab-3-part-2). This is a planning checklist, not student reflection or evidence of completed user testing.

| Requirement | Current evidence | Remaining work |
| --- | --- | --- |
| Redesign using collected data and Part 1 feedback | Existing box concept and six dialogue panels; technical timing improvements | Supply actual Part 1 trial observations/feedback, identify a concrete issue, and justify a revision from that evidence |
| Consider interaction beyond speech; distinguish listening/thinking | Participant status screen implemented and checked in a browser | Verify visibility and understanding on the actual Pi display; confirm any applicable instructor clarification before deciding optional hardware scope |
| New storyboard, diagram and/or script | Existing six-panel dialogue JSON | Revise the storyboard/script after selecting evidence-based changes; explicitly mark waits and wizard decisions |
| Raspberry Pi, one or more sensors, spoken interaction | Pi backend targets local mic/VAD/Whisper/Piper | Deploy safely and verify the physical microphone path; microphone is the proposed sensor, subject to course interpretation |
| Explain how the system works | Controller README and architecture description | Add actual hardware arrangement and tested setup details |
| Video or screencaptures of system and controller | Windows simulation screenshots only | Capture the real Pi system and wizard operation, clearly distinguishing demonstrations from participant trials |
| At least two people interact | No participant trial evidence in this checkpoint | Conduct and document at least two real sessions |
| Four reflection questions | Intentionally not answered | Student writes from actual observations: system strengths/weaknesses, controller strengths/weaknesses, lessons for autonomy, and possible dataset/modalities |

## Recommended next iteration

First establish a usable Pi-based Wizard-of-Oz study: verify the current microphone/speaker loop and visible state display, then use manual replies to explore what participants actually say. The existing fixed automatic reply is useful for exercising the technical loop but is not a general dialogue policy. Expanding to a language model is not required by the published Part 2 instructions.

Before altering the dialogue, obtain the student's Part 1 observations and instructor feedback. Use those to choose one focused wording/timing/recovery change and update the storyboard. Keep the current 2.0-second onset and 0.8-second silence settings as a documented baseline until evidence or the student supports a change.

After two real sessions, use the observations to prioritize further autonomy. Do not infer or fabricate participant findings from dry-run transcripts. Do not enable recording, add persistent data collection, install models, or deploy to the Pi merely because these actions appear in a checklist; those are separate operational steps.

A historical handoff cites an instructor message saying LED/controller is optional, but the exact scope has not been checked live in this review. The official repository still asks for system/controller documentation. Preserve that uncertainty rather than treating the whole requirement as waived.
