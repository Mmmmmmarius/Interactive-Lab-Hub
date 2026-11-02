# Detection data

[detection.json](detection.json) records the actual Pi inference on the selected street photo.

| Item | Recorded value |
| --- | --- |
| Input dimensions | 2880 × 2160 |
| Model input | 640 × 640 |
| Confidence threshold | 0.25 |
| Person detections | 6, including a billboard portrait |
| Bus detections | 1 |
| Traffic-light detections | 1 |
| Preprocessing | 8.8 ms |
| Inference | 125.8 ms |
| Postprocessing | 2.4 ms |
| Full prediction call | 1.554 seconds |

The file includes each box's coordinates and confidence, the input SHA-256, the Pi hostname and the saved output location. It contains no live-camera measurement.
