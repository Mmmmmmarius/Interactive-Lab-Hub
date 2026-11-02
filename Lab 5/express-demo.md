# Touch grass: 15-minute express demo

This demo uses 15 minutes of real photographs to present a simulated day's result. It is not a full-day measurement. Marius requested this mode. The provisional simulated period is 08:00–20:00, and normal daily rules are unchanged.

The first demo is complete. Both physical button presses and all 30 photographs are recorded. See the [run record](evidence/express-demo/run-222640-878587/README.md) for actual results and screenshots. Chair occlusion caused missed detections, and the model scored the result incorrectly, so it is not an accurate presence-duration measurement. Rerun instructions remain below. Use the rerun command before starting again.

Reanalysis of the second run's photographs has passed. The improved input supplies detection counts and the sampling interval to Qwen. The model still generates duration and score, and the program only validates or rejects them. The final result is 552 simulated minutes and 100 points. See the [reanalysis record](evidence/express-demo/qwen-replay-v3/README.md) for details and screenshots. No new capture is needed to view it. Five missed detections remain a limitation.

## How the demo works

| Item | Express demo | Daily mode |
| --- | --- | --- |
| Start | First Mini PiTFT button press. | 08:00 New York time each day. |
| Sampling | One photograph every 30 seconds, up to 30 in 15 minutes. | One photograph every five minutes. |
| Stop capture | Automatically after 15 minutes. | Button press before bed. |
| Start analysis | Another button press after capture ends. | The same bedtime button press. |
| Time used in analysis | One photograph represents 24 simulated minutes. | One photograph represents its five-minute actual sampling interval. |
| Report | Desk time and a 0–100 score for a simulated 08:00–20:00 day. | Estimated time and score from the actual daytime record. |

Original images and logs retain real capture times. Simulated times are stored separately without changing image timestamps. Python schedules capture, maps time labels and saves data. Qwen still calculates desk time and score. The model can make arithmetic errors, so compare the final answer with the records.

## Before starting

Keep the Pi, USB camera and Mini PiTFT powered. Aim the camera at the seat with your body visible, avoiding a chair back that obscures most of it. Close any previous YOLO or gesture demo using the camera. Connect the computer or phone to the same LAN.

Open or refresh the [Touch grass page](http://192.168.1.39:8080). **Express demo is armed** means the system is ready but has not started taking photographs. If the page was already open, refresh it to load the updated demo interface.

## Manually viewing live YOLO

In TigerVNC, open the terminal from the Pi desktop's top bar and run these commands. They use the original course script with the same detection parameters as the current capture analysis.

```bash
cd "/home/pi/Interactive-Lab-Hub-Lab5/Lab 5"
.venv/bin/python yolo_person.py --imgsz 320 --conf 0.4
```

The YOLO window shows live video and detection boxes. Click that window and press **q** to exit and release the camera before pressing the Mini PiTFT button to begin the 15-minute capture.

Live preview and scheduled capture are separate programs and currently do not share a video stream. Running both may cause camera contention and missed captures. TigerVNC and the LAN page can stay open during capture; only live YOLO needs to exit.

## One complete run

1. **First press.** Press either Mini PiTFT button once. The screen should show Express demo and the remaining time, and the page should show Capturing. Wait until the countdown starts before following the movement schedule below.
2. **First four minutes.** Sit at the desk normally. The page's photo count should increase.
3. **Minutes four through eleven.** Leave the camera's view. Do not simply hide behind the chair, since occlusion can confuse detection.
4. **Last four minutes.** Return to the desk. Capture stops automatically at 15 minutes. The page should show **15-minute capture finished**, and the screen should show **Press to analyze**.
5. **Second press.** Press either button again, simulating handing the day's data to the device before bed. The screen shows Processing, and the page shows detection and Qwen analysis status. The first 30-photo batch took about 36 seconds to analyze; still allow a few minutes for another run. A failure appears as an error, not a valid score.
6. **Review and record.** When **Your simulated report is ready** appears, record the simulated duration, score and explanation. Expand the images, timeline and original response and compare them with your actual exits and returns.

This movement schedule is a suggestion, not a record of actions already performed. Do not invent results to match an expected score. Missed captures are marked unknown, and the program does not fabricate scheduled photographs.

Allow about 20 minutes for the demo, with extra time if model analysis takes longer. The browser can be closed while waiting; the Pi continues processing in the background.

## What to retain in the README

- Actual capture start, end, successful photograph count and failures.
- When you actually left and returned, including deviations from the suggested schedule.
- Both Mini PiTFT inputs and screen confirmations. Start, capture-end and report clips can be combined into a short video.
- A web-result screenshot, the original model response and logs.
- A clear statement that this is a 15-minute compressed-day demo using simulated time, not a real full-day measurement of computer use.

The README already records this run's actual result, screenshots, the user's estimate of about 70% presence, and the detection and scoring errors. Save each rerun separately instead of overwriting that record.

## Rerunning and restoring daily mode

The first demo is complete. For a future rerun, execute this in Windows PowerShell:

```powershell
ssh cornell-pi "python3 /home/pi/touch-grass/control.py demo"
```

Then follow the two-button sequence above. Each run is stored in a new `store/demos/` subdirectory, preserving earlier data.

If the physical button is temporarily unresponsive, the same input can be sent from PowerShell. Execute it once to start capture and again after the 15 minutes end. The event is explicitly logged as a software trigger:

```powershell
ssh cornell-pi "python3 /home/pi/touch-grass/control.py press"
```

Check the current state:

```powershell
ssh cornell-pi "python3 /home/pi/touch-grass/control.py status"
```

Exit the demo early and restore daily mode:

```powershell
ssh cornell-pi "python3 /home/pi/touch-grass/control.py daily"
```

Exiting does not delete data. If analysis is running, the command asks you to wait until it finishes. Demo mode yields to normal capture at the next 08:00. Saved demos remain selectable on the page.

## Deployment record

Deployment reused the existing environment without installing dependencies. It first checked that no batch was processing, backed up the application, uploaded changes and restarted both services. After software checks passed, the demo was armed without pressing the start button on the user's behalf.

At deployment, Pi files matched local source and both services were running. Checks passed for timing, the two presses, recovery after restart, simulated-time mapping and data isolation. The initial Armed state is documented in the [preparation check](evidence/express-demo/preparation-check.md). Actual execution and browser screenshots are in the run record linked at the top.
