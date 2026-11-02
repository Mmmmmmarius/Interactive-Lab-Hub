"""Run the existing Pi NCNN model once on Marius's supplied still image."""
import hashlib
import json
import os
from pathlib import Path
import socket
import time
from collections import Counter
from datetime import datetime

os.environ.update(LANG='C.UTF-8', LC_ALL='C.UTF-8', PYTHONIOENCODING='utf-8', OMP_NUM_THREADS='4', MPLBACKEND='Agg')
lab = Path('/home/pi/Interactive-Lab-Hub-Lab5/Lab 5')
source = lab / 'user-street-input.png'
model_path = lab / 'yolo26n_ncnn_model'
records = Path('/home/pi/lab5-setup-records/user-image')
assert source.is_file(), source
assert model_path.is_dir(), model_path
records.mkdir(exist_ok=True)
os.chdir(lab)

import cv2
import torch
from ultralytics import YOLO

torch.set_num_threads(4)
model = YOLO(str(model_path))
started = time.monotonic()
result = model.predict(source=str(source), imgsz=640, conf=0.25, save=True,
                       save_txt=True, save_conf=True, project=str(lab / 'runs'),
                       name='part-a-user-street', exist_ok=False)[0]
elapsed = time.monotonic() - started
detections = [
    {'class': result.names[int(box.cls.item())],
     'confidence': round(float(box.conf.item()), 5),
     'xyxy': [round(float(x), 2) for x in box.xyxy[0].tolist()]}
    for box in result.boxes
]
outputs = [p for p in Path(result.save_dir).iterdir()
           if p.is_file() and p.stem == source.stem
           and p.suffix.lower() in {'.jpg', '.jpeg', '.png'}]
assert len(outputs) == 1, outputs
output = outputs[0]
image = cv2.imread(str(source))
assert image is not None
report = {
    'verified_at': datetime.now().astimezone().isoformat(),
    'hostname': socket.gethostname(),
    'input': str(source),
    'input_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'input_dimensions': {'width': image.shape[1], 'height': image.shape[0]},
    'model': str(model_path),
    'settings': {'imgsz': 640, 'conf': 0.25, 'torch_num_threads': 4},
    'counts': dict(Counter(d['class'] for d in detections)),
    'detections': detections,
    'speed_ms': result.speed,
    'predict_call_seconds': round(elapsed, 3),
    'output': str(output),
    'save_directory': str(result.save_dir),
    'webcam_used': False,
}
(records / 'detection.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print('USER_IMAGE_RESULT ' + json.dumps(report), flush=True)
