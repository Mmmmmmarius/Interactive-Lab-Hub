# Part C user video review

Marius supplied `WayVNC - TigerVNC 2026-11-01 19-18-22.mp4` and confirmed that the adjusted control looked correct. The unchanged source recording is retained in the local evidence archive. This repository includes the compressed playback copy linked below. The smaller [README playback copy](../../assets/part-c/hand-volume-demo.mp4) retains the full timeline and the original audio stream, with H.264 video compressed at CRF 20 and 30 frames per second. No scenes were added, trimmed or reordered; frame cadence changes during transcoding.

## Visible sequence

- Approximately 0–8 seconds: the demo is open and the person approaches the camera.
- At 9.500 seconds: visible hand landmarks, thumb-to-index line and 71% on the volume indicator.
- At 10.500 seconds: the hand is spread and the indicator reaches 100%.
- At 13.500 seconds: the thumb and index finger pinch together; the marker is green and the indicator reads 0%.
- From approximately 14–23 seconds: repeated open-and-pinch movements return to 100% and 0%, with an intermediate reading also visible as the hand turns.
- Approximately 24–28 seconds: the person moves away and the indicator is at 0%.

The full timeline was inspected using one-second review frames, followed by full-resolution inspection of the three exact extraction times. These images show the displayed control response. They are not measurements of acoustic loudness, accuracy across distances or sustained inference speed.

## Screenshots and evidence boundaries

The three README screenshots are direct video-frame extractions, cropped to the same demo-window rectangle: x=216, y=96, width=644, height=568 pixels. Text, landmarks and percentages were not redrawn or modified.

The source contains an AAC audio stream, but decoding both stereo channels to PCM produced only zero-valued samples. No audible volume comparison is claimed from this recording. The selected 0% frame is a thumb-index pinch, not the separate Quiet Coyote condition. The course's Quiet Coyote message was not visible in the reviewed sequence.

The personal application idea remains for Marius to supply. The rest of Part C now includes the observed problem, the limited calibration change, a playback link, screenshots and an explanation of the landmark-to-volume mapping.

[review.json](review.json) records the source and output hashes, extraction times, crop, media properties and checks. The original capture was left unchanged in the local archive.
