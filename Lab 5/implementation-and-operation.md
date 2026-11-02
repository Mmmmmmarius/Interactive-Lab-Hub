# Touch grass score: implementation and operation

This page documents the project's implementation and operation. It does not replace the personal storyboard and actual feedback for Part F. Execution results appear below; a design description alone does not establish a completed hardware test.

## Confirmed daily workflow

Capture starts at 08:00 New York time each day, saving one photograph every five minutes. Before bed, press either Mini PiTFT button to stop that day's capture and begin processing. A held button counts once, and additional presses during processing do not create another job. A new batch starts at 08:00 the next morning.

A press after midnight but before 08:00 still processes the batch that started at 08:00 the previous day. If a day is missed, its data is retained and the next day gets a separate batch. Missing photographs are never fabricated. After the first deployment, normal capture begins at the next 08:00.

YOLO converts each sample into a person-detection record. Python totals the present, absent and unknown samples and supplies those counts and the sampling interval to Qwen. Qwen calculates desk minutes and a 0–100 score and generates an explanation.

Python validates fields, counts, arithmetic relationships, score limits and simulation labels. Validation only accepts or rejects a result. It does not replace, correct or generate the model's duration or score. A failure allows up to three requests, with each prompt, original response and rejection reason saved separately. If all three fail, the page requests review instead of inserting a program-calculated result.

To use a consistent daily scale, the prompt currently applies an implementation scale proposed by Codex: 0 hours is 0 points, 2 hours is 25, 4 hours is 50, 6 hours is 75, and 8 hours or more is 100. Qwen performs the conversion. This is an adjustable implementation parameter, not a course rule or an eight-hour target previously specified by the user.

The fixed camera faces the desk. This version detects people across the full view, without identifying them or proving that a detected person is using the computer. Sampling, occlusion and model arithmetic can all introduce errors. Short checks are labeled Setup test and do not count as full-day records.

The current model is the installed `qwen3:0.6b`, with thinking enabled. The prompt expresses the score as desk minutes divided by 4.8, rounded to an integer and capped at 100. This is equivalent to the eight-hour scale, and Qwen still performs the arithmetic. `qwen3.5:0.8b` made calculation errors with thinking disabled and did not return a final answer within this round's budget with thinking enabled. Both comparisons are retained.

## File locations

- Windows source: `Study HQ/Projects/INFO5345/Lab5/touch_grass/`.
- Pi application: `/home/pi/touch-grass/`.
- Pi data: `/home/pi/touch-grass/store/days/<date>/`.
- Each daily `day.json` stores actual sampling times, status and results. `photos/` stores the photographs.
- Each processing run's `jobs/<job-id>/` stores detections, `night_log.jsonl`, structured input, the full prompt, the Ollama response and the original answer. The newer version also saves each request and validation in `attempt-1` through `attempt-3`. The night log records processing of daytime photographs; its timestamps remain the actual capture times.
- The original course scripts are unchanged. The old `piscreen.service` files are retained, and its application remains at `/home/pi/screen_boot_script.py`.

## Deployment steps

No existing local deployment guide covered this Pi project, so this workflow was written before execution. It reuses the existing Python environments without installing new packages.

1. Copy the source to its separate Pi application directory. The main program uses the Lab 5 virtual environment, while the screen program uses the existing `/home/pi/venv`.
2. Set the first capture date in New York time, model directory, data directory and web port in `config.json`. The default port is 8080.
3. Run `app.py --prepare-test` to take three short-check photographs, saved as a separately labeled test batch for that date. Normal scheduled capture still waits for the configured first date.
4. Create `touch-grass.service` and `touch-grass-screen.service`. The new screen service conflicts with `piscreen.service`, so stop the old service while retaining its configuration, then start the new one. Restore the old service if deployment fails.
5. Check the LAN page, original data and screen program status. After startup checks pass, enable the services at boot. Keep the old screen service disabled to avoid concurrent GPIO access. Marius verifies the physical buttons separately; a service heartbeat does not establish button acceptance.

## Operation and recovery

The separate [15-minute express demo](express-demo.md) starts real capture with the first button press, takes one photograph every 30 seconds and stops at the time limit. A second press starts analysis. Each slot represents 24 simulated minutes, producing a simulated 08:00–20:00 day. Actual samples and simulation labels are saved separately. Demos use `store/demos/` and do not overwrite normal records in `store/days/`.

Open the [Touch grass LAN page](http://192.168.1.39:8080) to view the date, status, estimated duration, score and original records. Processing is started with the physical button. The router assigns the current address; if the Pi's address changes, use the new one.

```bash
sudo systemctl status touch-grass.service touch-grass-screen.service
sudo journalctl -u touch-grass.service -u touch-grass-screen.service -n 40 --no-pager
```

To stop this project and restore the original network-information screen:

```bash
sudo systemctl disable --now touch-grass-screen.service touch-grass.service
sudo systemctl enable --now piscreen.service
```

Stopping this way preserves photographs and original reports. Photographs remain on the Pi, and Marius decides when to remove demo data. The web control endpoint does not provide file deletion.

## Current validation status

The latest reanalysis passed. Qwen produced 552 simulated minutes and a score of 100 from the same 30 photographs. The batch took about 34 seconds, and the page was checked. Photographs, detection labels and earlier incorrect reports are unchanged. See the [reanalysis record](evidence/express-demo/qwen-replay-v3/README.md) for details and screenshots. Earlier checks are retained below.

- Windows and Pi checks passed for date assignment, daylight-saving boundaries, no historical backfilling, no capture after stopping, held-button debounce, empty data, duplicate presses and model-output validation.
- Both new services started and were enabled at boot. The old screen service was disabled with its files retained. The LAN page, desktop and narrow layouts, original-image access and HTTP access restrictions were checked.
- A software trigger completed the real queue, YOLO detection, Qwen request, report saving and page update. The final model returned 0.1 minutes and 0 points, consistent with this short record. Earlier incorrect answers and adjustments are in the [setup check](evidence/touch-grass-build/README.md).
- Two physical presses actually triggered the 15-minute demo. All 30 photographs were saved, and the report completed about 36 seconds later. See the [run record](evidence/express-demo/run-222640-878587/README.md) for results and page screenshots. The TFT service remained running, but no close-up confirms its specific screen states.
- Only one photograph in that run was detected as containing a person, inconsistent with Marius's observation that he was present for about 70% of the time. The photographs show the chair back obscuring his upper body. A larger input size still detected one image from the same batch; a lower threshold detected four. Marius then adjusted the framing. The second run detected 23 images but still missed five with a visible person. Detection settings were unchanged.
- Qwen returned 24 simulated minutes and 50 points. The configured scale gives 5 points for 24 minutes, and the model also incorrectly claimed there were unknown samples. The original response is retained. Format and range checks do not replace an accuracy review.
- A full day of capture followed by nighttime processing has not yet been completed.

## Building and deploying the grass-pet page

Grass bro is deployed on the [Pi LAN page](http://192.168.1.39:8080/). Duration and score come from the existing Qwen report. Clicking the pet only changes frontend copy. The current demo remains at 552 simulated minutes and 100 points. New screenshots and deployment records are in the [UI checks](evidence/grass-ui/README.md).

Source files are in `Study HQ/Projects/INFO5345/Lab5/touch_grass/ui/`. `grass-bro.js` defines the character and copy, `view-state.js` selects reports and states, and `page.js` handles page behavior. HTML and CSS are in the same directory. After editing the source, run these commands from the workspace root:

```powershell
node 'Study HQ/Projects/INFO5345/Lab5/touch_grass/build-ui.cjs'
node 'Study HQ/Projects/INFO5345/Lab5/touch_grass/test-ui.cjs'
```

The build generates `web/index.html`, `web/style.css` and `web/app.js`. The Pi service already exposes these three files, so the character is bundled into the script without new routes, packages or external resource requests.

Back up the Pi's `web/` before deployment. This round's previous page is saved at `/home/pi/touch-grass/backups/grass-ui-20261102-012015/web/`. Upload new files with an `.incoming` suffix and atomically replace them one at a time, replacing HTML last. The service reads the new files on request, so refresh the browser without restarting capture or the TFT service. To restore the old UI, recover the same three files from that backup using the same temporary-file replacement procedure, then refresh.

This round verified that deployed files matched HTTP responses, backend and demo data were unchanged, both services retained their processes, and live YOLO remained running. Before the next camera capture, press `q` in the YOLO window to release the camera.
