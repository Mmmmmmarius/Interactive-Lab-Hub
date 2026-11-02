# Part A: selected street-photo test

The test ran on the Raspberry Pi after SSH connectivity returned following a restart. The cause of the earlier connection timeout was not established.

- Input: [user-provided PNG](../../assets/part-a/user-street-input.png), 2880 × 2160 pixels.
- Output: [annotated result](../../assets/part-a/yolo-user-street-result.jpg).
- Model: the existing `yolo26n_ncnn_model` in the Pi's Lab 5 environment.
- Settings: `imgsz=640`, `conf=0.25`, four PyTorch threads. The reported model input was 640 × 640.
- Result: six `person` boxes, one `bus` and one `traffic light`.
- Recorded inference time: 125.8 ms. The prediction call took 1.554 seconds, including work outside model inference.

The billboard portrait received a `person` box with confidence 0.79004. Many smaller or partly hidden pedestrians were not marked. These detections are not a count of people physically present, and this still-image test does not measure live-camera performance.

## Actual run records

- [Detection data](detection.json), including the input hash, boxes, confidence values, timing and Pi output path.
- [Readable detection summary](detection.md).
- [Successful terminal output](inference-log-verified.txt).
- [YOLO label file](user-street-input.txt).
- [Executed test script](user-photo-test.py).
- [File and document verification](verification.md).

The first inference produced the same class counts, but the recording script expected a PNG output filename while Ultralytics saved a JPEG. The [first log](inference-log.txt) retains that assertion failure. The script was corrected to use the actual saved image filename, then rerun successfully. The README reports the successful recorded run, and both run folders remain on the Pi.

No packages or models were installed for this retest. The original public-sample results remain in the earlier Part A evidence. This update covers local documentation and the Pi run; it does not publish to GitHub.
