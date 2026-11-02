# Lab 5 Part A environment and models

Part A's software preparation, two-image detection and screenshot records are complete. The editable main document is the [Lab 5 README](../../README.md). Detailed versions and original results are in [preparation-status.json](preparation-status.json).

## Entering the environment

First connect from a Windows terminal:

```powershell
ssh cornell-pi
```

Then run these commands in the Pi terminal:

```bash
cd '/home/pi/Interactive-Lab-Hub-Lab5/Lab 5'
source .venv/bin/activate
ollama list
```

This directory is a separate Git worktree. The original repository remains at `/home/pi/Interactive-Lab-Hub`, with its existing uncommitted Lab 3 and Lab 4 files unchanged.

## Prepared components

| Component | Version or location | Verification |
| --- | --- | --- |
| System | Pi 5, 8 GB, Debian 12 ARM64, Python 3.11.2 | About 35 GB free. Power status was normal after verification. |
| Python environment | `Lab 5/.venv` | Course dependency imports and `pip check` passed. |
| MediaPipe | 0.10.18 | The Hands graph initialized and processed a blank test frame. A live hand-gesture experiment had not yet been performed. |
| OpenCV | 4.11.0.86 | Same version as OpenCV-contrib, with NumPy 1.26.4. |
| PyTorch | 2.14.1+cpu | Official CPU build. Tensor computation passed. |
| YOLO | Ultralytics 8.4.188, YOLO26n | Weights downloaded and exported to `yolo26n_ncnn_model`. |
| Ollama | 0.40.11 | Service enabled, with the API listening only on localhost. |
| Qwen | `qwen3.5:0.8b`, `qwen3:0.6b` | Both run locally. Image input was also verified for the former. |

## Image detection

```bash
yolo predict model=yolo26n_ncnn_model source=part-a-bus.jpg project="$PWD/runs"
yolo predict model=yolo26n_ncnn_model source=snap.jpg project="$PWD/runs"
```

- [Bus detection result](../../assets/part-a/yolo-bus-result.jpg): four people and one bus detected.
- [Second-image result](../../assets/part-a/yolo-second-image-result.jpg): two people and one tie detected.
- `snap.jpg` is identical to `zidane.jpg` downloaded from the official Ultralytics site and is available for subsequent image-input tests.

The October 26 course CLI checks passed, with single-inference times of 66.2 ms and 112.1 ms. Commands and raw output are in [part-a-cli-yolo-local.txt](part-a-cli-yolo-local.txt). Results are stored on the Pi in `Lab 5/runs/part-a-cli-bus` and `Lab 5/runs/part-a-cli-second`. The initial `project=runs` record is also preserved. The path was then made absolute to keep outputs inside Lab 5.

Both inputs are public examples. These checks did not use the camera or perform the live interactions for Parts B and C.

## Model execution checks

The [Ollama verification record](ollama-verification.json) retains all original responses. `qwen3.5:0.8b` answered the arithmetic question correctly and identified the main vehicle in the image as a bus. `qwen3:0.6b` answered the first arithmetic prompt incorrectly but answered correctly after rephrasing. The models run, but their answers still require review in Part D.

The course-required [ollama list screenshot](../../assets/part-a/ollama-list.png) and [YOLO terminal screenshot](../../assets/part-a/yolo-cli.png) have been added to the main document. They were captured directly from the Pi's LXTerminal with a desktop screenshot tool. Uncropped desktop originals are retained in this directory.

Both models, the Ollama service and dependency checks were reconfirmed on October 26. Earlier installation and model-response records are retained. Camera experiments had not yet been run at that stage.

## Installation records

- [Installed versions](requirements-installed.txt).
- [Pi compatibility constraints](pi-constraints.txt).
- [Python environment verification](environment-verification.json).
- [YOLO verification](yolo-verification.json).
- [System status](final-system-status.json).

The initial default dependency resolution selected CUDA packages. Installation was stopped before those packages were installed, then switched to the official CPU source. One model download error was recovered by resuming the download. UTF-8 settings were added to the Pi's `.bashrc` and verified again. The original course requirements file was unchanged.

Sources: [course Part A](https://github.com/IRL-CT/Interactive-Lab-Hub/blob/Fall2026/Lab%205/README.md#part-a), [PyTorch CPU installation](https://pytorch.org/get-started/locally/#no-cuda), and [Ollama Linux installation](https://docs.ollama.com/linux).
