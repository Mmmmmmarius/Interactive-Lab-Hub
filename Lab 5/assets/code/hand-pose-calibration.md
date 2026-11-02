# Part C calibration change

The [patch](hand-pose-calibration.patch) records the changes from the course's `hand_pose.py` to the separate `hand_pose_calibrated.py` used in the recorded demonstration. The original course script remains unchanged.

Codex introduced `PINCH_MIN_PX = 50` and `PINCH_MAX_PX = 120`, then used those constants in the three mappings for audio volume, bar height and displayed percentage. The course version used 50–300 pixels. No tracking or Quiet Coyote rules changed.

This is a patch for the existing Lab 5 environment, not a standalone hand-tracking application. It uses the course's `HandTrackingModule.py`, `loop_audio.sh`, camera and audio setup. Run the calibrated copy from the Lab 5 directory in the Pi's graphical desktop. The pixel range depends on hand distance and angle.

The local calibrated source matches the hash saved when it was deployed to the Pi. The [deployment record](../../evidence/part-c-setup/live-hand-calibrated.md) and [video review](../../evidence/part-c-video/review.md) describe the actual result. The patch was exported for documentation without starting a new hardware test.

Course source: [IRL-CT Interactive-Lab-Hub, Lab 5 hand_pose.py](https://github.com/IRL-CT/Interactive-Lab-Hub/blob/Fall2026/Lab%205/hand_pose.py). The custom change is attributed to Codex in the main README.
