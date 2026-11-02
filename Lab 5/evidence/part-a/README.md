# Lab 5 Part A 环境与模型

Part A 的软件准备、两张图片检测和截图记录已经完成。本地可编辑正文在 [Lab 5 README](../../README.md)。详细版本和原始结果见 [preparation-status.json](preparation-status.json)。

## 进入环境

先在 Windows 终端连接：

```powershell
ssh cornell-pi
```

然后在 Pi 终端运行：

```bash
cd '/home/pi/Interactive-Lab-Hub-Lab5/Lab 5'
source .venv/bin/activate
ollama list
```

这个目录是独立 Git worktree。原仓库仍位于 `/home/pi/Interactive-Lab-Hub`，其中既有的 Lab 3 和 Lab 4 未提交文件保持原状。

## 已准备的内容

| 内容 | 版本或位置 | 验证结果 |
| --- | --- | --- |
| 系统 | Pi 5、8 GB、Debian 12 ARM64、Python 3.11.2 | 剩余约 35 GB，验证后供电状态为正常。 |
| Python 环境 | `Lab 5/.venv` | 课程依赖导入和 `pip check` 通过。 |
| MediaPipe | 0.10.18 | Hands 图初始化并处理空白测试帧成功，尚未做真人手势实验。 |
| OpenCV | 4.11.0.86 | 与 OpenCV-contrib 使用相同版本，NumPy 为 1.26.4。 |
| PyTorch | 2.14.1+cpu | 官方 CPU 版本，张量计算通过。 |
| YOLO | Ultralytics 8.4.188、YOLO26n | 已下载权重并导出 `yolo26n_ncnn_model`。 |
| Ollama | 0.40.11 | 服务已启用，API 只监听本机。 |
| Qwen | `qwen3.5:0.8b`、`qwen3:0.6b` | 两者均可本地推理，前者的图片输入也已验证。 |

## 图片检测

```bash
yolo predict model=yolo26n_ncnn_model source=part-a-bus.jpg project="$PWD/runs"
yolo predict model=yolo26n_ncnn_model source=snap.jpg project="$PWD/runs"
```

- [公交车检测结果](../../assets/part-a/yolo-bus-result.jpg)：检测到四个人和一辆公交车。
- [第二张图片检测结果](../../assets/part-a/yolo-second-image-result.jpg)：检测到两个人和一条领带。
- `snap.jpg` 与从 Ultralytics 官网下载的 `zidane.jpg` 内容一致，可供后续图片输入使用。

10 月 26 日的课程 CLI 检查通过，单次推理时间分别为 66.2 ms 和 112.1 ms。命令和原始输出见 [part-a-cli-yolo-local.txt](part-a-cli-yolo-local.txt)。检测结果分别保存在 Pi 的 `Lab 5/runs/part-a-cli-bus` 和 `Lab 5/runs/part-a-cli-second`。首次使用 `project=runs` 的记录也已保留，随后改用绝对路径让输出留在 Lab 5 目录。

两张输入均是公开示例。没有调用摄像头，也没有进行 Part B、C 的真人交互实验。

## 模型运行验证

[Ollama 验证记录](ollama-verification.json)保留了所有原始回答。`qwen3.5:0.8b` 正确回答算术问题，并把图片中的主要车辆识别为 bus。`qwen3:0.6b` 首次算术回答错误，改写问题后回答正确。模型已能运行，但仍需在 Part D 检查回答内容。

课程要求的 [ollama list 截图](../../assets/part-a/ollama-list.png)与 [YOLO 终端截图](../../assets/part-a/yolo-cli.png)已补入正文。截图来自 Pi 的 LXTerminal，使用桌面截图工具直接捕获终端区域。未裁切的桌面原图也保存在本目录。

10 月 26 日重新确认了两款模型、Ollama 服务和依赖检查。此前的安装和模型回答记录继续保留，摄像头实验未运行。

## 安装记录

- [实际安装版本](requirements-installed.txt)。
- [Pi 兼容性约束](pi-constraints.txt)。
- [Python 环境验证](environment-verification.json)。
- [YOLO 验证](yolo-verification.json)。
- [系统状态](final-system-status.json)。

首次默认依赖解析选中了 CUDA 包，已在安装前停止，随后使用官方 CPU 安装源。一次模型下载错误通过续传恢复。已在 Pi 的 `.bashrc` 添加 UTF-8 设置，并重新验证。原始课程依赖文件保持不变。

依据：[课程 Part A](https://github.com/IRL-CT/Interactive-Lab-Hub/blob/Fall2026/Lab%205/README.md#part-a)、[PyTorch CPU 安装说明](https://pytorch.org/get-started/locally/#no-cuda)、[Ollama Linux 安装说明](https://docs.ollama.com/linux)。
