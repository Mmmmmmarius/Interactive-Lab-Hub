# Touch grass: grass-pet and UI redesign proposal

Status: Marius approved this proposal on November 2, and the interface is deployed to the Pi. Actual screenshots and checks are in the [deployment record](evidence/grass-ui/README.md). The original proposal is retained below as the basis for this design iteration.

[Open the interactive grass-pet state preview](ui-preview/grass-states.html). Five score bands and six operating states use the same character. Click the pet to cycle through captions, or use the slider to compare score bands.

Task: T088. This follows the [Lab 5 project brief](project-brief.md). Marius requested a grass pet, score-dependent behavior and meme copy. He approved the following character, score bands and wording.

## Recommended direction

Use a small grass character with expressive, slightly cheeky reactions. It acts like a desktop pet that cannot resist commenting on the record. Keep the entire UI in English, with concise functional explanations and humor concentrated in the pet and speech bubble.

The working name is **Grass bro**. Its body is a small tuft of grass, with three long leaves defining its silhouette, half-open eyes, a small mouth, thin arms and short legs. Keep one recognizable character and distinguish states through gaze, posture and bent leaves.

Use a two-dimensional cartoon style: a grass-green body, dark-green outlines, a pale-blue background and small yellow accents. The pet, speech bubble and score form one scene, followed by a line of duration and sampling information, then the detection timeline.

### Scores and expressions

The score continues to represent desk time. A higher score prompts a stronger suggestion to leave the desk. These five visual bands do not change the scoring formula.

| Score | Pet expression | Default bubble | Alternative copy in the same band |
| --- | --- | --- | --- |
| 0–24 | Relaxed leaves and arms, with a slight smile. | `we're chillin.` | `no roast today.`<br>`looking pretty chill, brother.` |
| 25–49 | One raised eyebrow, head tilted toward the score. | `locked in, huh?` | `interesting chair commitment.`<br>`the chair has your attention.` |
| 50–74 | Hands on hips, pointing a leaf at itself. | `touch some grass, brother.` | `i'm grass. i'm right here.`<br>`the chair can wait.` |
| 75–99 | Wide eyes, then a slow sideways look as the leaf tips droop. | `are we deadass rn?` | `bro. the chair isn't going anywhere.`<br>`outside is still a thing.` |
| 100 | An exaggerated slump, drooping leaves and a small white flag. | `bro is fully cooked.` | `the chair won.`<br>`touch some grass, brother. seriously.` |

Each report starts with the band's default line. Only clicking the pet changes the caption and triggers a brief movement, avoiding repeated copy changes on automatic refresh. Clicking does not alter the score, duration or report.

A low score only means less model-estimated desk time. It does not establish that the user went outside, exercised or touched grass. High-score remarks are playful feedback, not a health diagnosis.

## Page layout and copy

On desktop, place the pet and speech bubble on the left, with the score and duration on the right. On a phone, stack the pet, score and timeline in that order. The pet is the largest visual element on the first screen.

```text
Touch grass.                              Recorded day

Simulated day · 15-minute capture

  “bro is fully cooked.”                   Touch grass score
                                           100 / 100
       [Grass bro slumps with a flag]      Higher = more desk time.

Simulated desk time: 552 min                30 photos

The receipts
[Detection timeline and clear text legend]

Show the receipts: photos + original Qwen answer
```

The example values come from the saved second-run reanalysis and illustrate the layout. They represent a simulated day based on 15 minutes of capture, not a real full-day record.

| Existing content | Proposed content | Functional explanation to retain |
| --- | --- | --- |
| Fixed introductory heading | A pet bubble selected from the valid report's score band. | Keep `Touch grass score` and `Higher = more desk time.` visible. |
| Waiting to start | `ready when you are, brother.` | Explicitly say to press the Mini PiTFT button to begin capture. |
| Capturing | `gathering the receipts.` | Show actual sample count, remaining time and current mode. |
| Capture complete | `the receipts are in.` | Explicitly say to press the Mini PiTFT button again to start analysis. |
| Processing | `let me cook.` | Show whether photographs are being read or time is being estimated, without inventing a completion percentage. |
| Detection-record heading | `The receipts` | Keep `Person detected`, `No person detected` and `Unknown` in the legend. |
| Collapsible evidence access | `Show the receipts: photos + original Qwen answer` | Retain original images, original timestamps and unmodified model answers. |
| Arithmetic validation failure | `that math ain't mathing.` | Explain that the report failed validation, its original answer was saved, and how to retry. |
| Device disconnected | `bro? you there?` | Clearly indicate that the Pi connection is lost and suggest checking power and the shared network. |

No report, processing failure and offline each have separate states. Do not use a zero score or low-score pet as a substitute for success. If an old report remains visible while offline, label it as the last saved result. Non-arithmetic errors should use their actual explanation instead of the arithmetic-failure message.

The main duration and score come from a valid Qwen answer. Pet remarks use a frontend copy library and are shown separately from the model's original summary. The original answer and uncertainty remain accessible. Keep the simulation label visible on the first screen, outside collapsed content.

### Visual parameters

| Purpose | Proposal |
| --- | --- |
| Page background | Cloud white `#F7FBFF`. |
| Pet scene | Pale blue `#D9EEFF`. |
| Grass body | Grass green `#71C940`. |
| Text and outlines | Dark green `#173A29`. |
| Hints and small details | Bright yellow `#FFD65A`. |
| Additional expression details | Pink `#EF8BB2`, used sparingly. |
| Headings | Bold rounded sans serif, preferring local Arial Rounded MT Bold, then Trebuchet MS and sans-serif. |
| Body and data | Trebuchet MS, then Arial and sans-serif. Body text starts at 16px. |
| Motion | One short expression change when switching reports, with another response on pet click. No continuous shaking or automatic sound. Respect reduced-motion settings. |

Local design references initially suggested a soft three-dimensional style and orange palette suited to children's products. That direction did not fit this project and was not adopted. The proposal instead uses two-dimensional cartoon expressions, emphasizing outlines only around the pet and bubble while keeping information areas simple.

## Implementation and acceptance

After approval, implement in the following order, with an estimated 45–75 minutes including browser checks and Pi deployment. Network troubleshooting is additional.

1. **Character and copy, about 15–25 minutes.** Use SVG to draw the same grass in five poses and organize score and operating-state copy. Keep the existing native HTML, CSS and JavaScript without a frontend framework or online asset dependency.
2. **Existing report integration, about 15–20 minutes.** Update layout and state rendering. Select expressions only from valid report scores and continue displaying Qwen's duration and score unchanged. Preserve sampling, model input and calculation validation behavior.
3. **Checks, deployment and documentation, about 15–30 minutes.** Review desktop and phone-width layouts, band boundaries, no-data, processing, error and offline states. Back up the old interface, deploy the static files and update the README with screenshots of the existing real report.

Code changes are scoped to `Study HQ/Projects/INFO5345/Lab5/touch_grass/web/` and pet assets added there. The deployment directory is `/home/pi/touch-grass/web/` on the Pi. This round changes the LAN page while preserving existing Mini PiTFT capture and processing functions.

Acceptance criteria:

- Scores 0, 24, 25, 49, 50, 74, 75, 99 and 100 select the correct bands. Invalid values do not produce a success state.
- A valid zero score is visibly distinct from no result. Connection loss displays an offline message.
- The current actual report displays 552 simulated minutes and 100 points unchanged, selecting the highest pet band. Other bands are checked with clearly labeled UI fixtures, not represented as additional experiments.
- Refreshing does not continually replay movement. The pet works with mouse, touch and keyboard input. States remain understandable with reduced motion.
- At 375px, 768px and desktop widths, body text and controls are readable without horizontal overflow.
- The README explains the UI iteration and AI assistance while preserving earlier errors and simulation labels. Static-file deployment does not close the existing YOLO preview.

### Online expression references

These supplementary sources were used to check meaning and real usage. Adapted project copy is not presented as a verbatim internet quote, and no people images or GIFs were downloaded from them.

- **touch grass** informally tells someone immersed in online activity to step away from the screen. The project retains Marius's `touch some grass, brother.` [BBC Learning English](https://downloads.bbc.co.uk/learningenglish/features/tews/231212_tews_touch_grass.pdf).
- **deadass** means serious or seriously here and is normally written as one word. [Dictionary.com](https://www.dictionary.com/culture/slang/deadass). A reaction-image example confirms usage of `are we deadass rn`. [Tenor example](https://tenor.com/view/are-we-deadass-rn-are-we-deadass-gif-9230393179388786087).
- **locked in** refers to intense focus. The middle-band `locked in, huh?` is adapted project copy. [Know Your Meme](https://knowyourmeme.com/memes/when-you-gotta-lock-in).
- **cooked** can exaggerate being in trouble or beyond help. `bro is fully cooked.` is the proposed highest-band remark, not a factual assessment of the user. [Know Your Meme](https://knowyourmeme.com/memes/cooked-getting-cooked).

Implementation result: completed in this direction. Source files are in the application's `ui/` directory, and `build-ui.cjs` generates the three static files in `web/`. Browser checks covered the current simulated report, short setup-test report, clickable captions, keyboard input, automatic refresh and four viewport widths. The browser had reduced motion enabled, so clicks changed copy without animation. Capture, model processing and live YOLO were not restarted.
