# Part C volume range calibration

Marius reported that fully spreading the thumb and index finger could not reach 100% on the displayed volume scale. The course script uses three identical interpolation ranges, 50 to 300 pixels, for the actual volume, bar and displayed percentage.

The previous session log contained 81 frames with nonzero mapped volume. Their recorded thumb-to-index distances had a median of 134 pixels and a maximum of 162 pixels. These samples are not labelled as deliberate maximum-spread poses. Together with the user's report, they motivated a conservative upper endpoint of 120 pixels for the current camera distance.

Codex prepared `hand_pose_calibrated.py`, replacing all three upper endpoints with 120 while retaining the lower endpoint at 50. No other gesture or tracking rules changed. The teacher's original file remains unchanged. The old process group and its audio loop were stopped before the calibrated copy was started.

```bash
cd '/home/pi/Interactive-Lab-Hub-Lab5/Lab 5'
source .venv/bin/activate
python hand_pose_calibrated.py
```

[Launch metadata](live-hand-calibrated.json) records the exact change, deployed hash and endpoint checks. Values at 20, 50, 85, 120 and 160 pixels mapped to 0%, 0%, 50%, 100% and 100%. The Pi checked that the deployed copy differed from the original only by the named constants and the three interpolation ranges. The [actual desktop capture](desktop-hand-calibrated.png) confirms the window is running, not successful full-spread gesture control. One audio playback stream was present.

The scale still depends on the hand's distance from the camera. This is a small range adjustment for the current setup, not automatic distance normalization. Marius subsequently confirmed that it looked correct and supplied a recording. The [video review](../part-c-video/review.md) documents visible 71%, 100% and 0% states and repeated opening and pinching. The separate Quiet Coyote trigger is not established by those pinch frames.
