# 15-minute demo preparation check

This file records preparation and deployment of the demo program, not demo results. The machine-readable record is [preparation-check.json](preparation-check.json). Instructions are in the [express demo guide](../../express-demo.md).

## Verified

- The eight demo source files on Windows and the Pi were byte-identical. Their hashes are saved in the JSON record.
- Ten automated checks passed on both systems, covering the existing schedule, midnight, daylight saving, held-button debounce, the new two-press flow, the 15-minute stop, repeated input, timer recovery after restart, demo isolation and the simulated time scale.
- Python compilation, JavaScript syntax and page-element reference checks passed.
- The LAN page and static files were accessible. Control requests without credentials were rejected. Invalid batch and image addresses returned not found.
- The main program and Mini PiTFT service were running. Service status, device state and the current batch are saved in JSON.
- The earlier three-photo setup check remained independently accessible. The new demo was Armed, with zero successful photographs and no model report yet.

## Data and time

Real capture lasts 900 seconds at 30-second intervals, for up to 30 photographs. Simulated time runs from 08:00 to 20:00, with each slot representing 24 minutes. Original photographs and detection logs keep actual capture times, while simulated times are stored separately. Qwen estimates duration and score; Python does not replace model values.

Demo records are stored in `/home/pi/touch-grass/store/demos/` on the Pi. Normal records remain in `store/days/`. The pre-deployment application backup is `/home/pi/touch-grass/install-backup/before-express-20261101-215637`. Normal schedule and model configuration values were unchanged, and no dependencies were added.

## Validation boundaries

This preparation check did not trigger camera capture or model analysis. The two physical presses, screen changes, detections and report accuracy needed to be observed during execution.

Browser automation returned `browser.user is unavailable`, and reconnecting timed out. This round therefore completed HTTP and source checks without new browser screenshots of the demo interface. Screenshots from the earlier setup check were not presented as new-demo evidence.

After execution, retain actual start and end times, photograph counts, exits and returns, button events, original model answers and result screenshots, then add the demo results to the README.
