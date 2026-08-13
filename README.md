# ComfyUI Intel XPU

Docker image for running [ComfyUI](https://github.com/Comfy-Org/ComfyUI) with native **PyTorch XPU acceleration on Intel Arc GPUs**.

This image was created primarily to make running ComfyUI on Intel Arc GPUs — including Intel Arc Pro Battlemage GPUs — straightforward on Docker and Unraid without requiring GPU passthrough to a virtual machine.

## Features

- Native PyTorch XPU acceleration
- Intel Level Zero GPU runtime
- Intel OpenCL runtime
- ComfyUI
- ComfyUI Manager
- Hugging Face CLI (`hf`)
- aria2 for fast/resumable downloads
- Persistent model storage
- Persistent custom nodes
- Persistent input/output directories
- Automatic creation of standard ComfyUI model directories
- Designed for Intel GPUs using the Linux `xe` driver
- Tested on Intel Arc Pro B70

## Tested Configuration

The initial release has been validated with:

| Component | Tested |
|---|---|
| GPU | Intel Arc Pro B70 32 GB |
| GPU architecture | Battlemage |
| Host OS | Unraid |
| Host kernel driver | `xe` |
| Container base | Ubuntu 26.04 |
| Python | 3.14 |
| PyTorch | Native XPU build |
| ComfyUI | Current upstream build |
| Test model | SDXL 1.0 Base |
| Test resolution | 1024 × 1024 |

The B70 was detected by PyTorch as:

```text
XPU available: True
XPU device count: 1
XPU 0: Intel(R) Graphics [0xe223]
```

ComfyUI reported approximately 31 GB of usable VRAM:

```text
Total VRAM 31023 MB
Device: xpu:0 Intel(R) Graphics [0xe223]
```

## Docker Image

```text
heroeswearkapes/comfyui-intel-xpu:latest
```

Versioned images are also published using the build date and upstream ComfyUI Git commit:

```text
heroeswearkapes/comfyui-intel-xpu:YYYY.MM.DD-<commit>
```

Example:

```text
heroeswearkapes/comfyui-intel-xpu:2026.08.13-b323a34
```

## Host Requirements

The Intel GPU must already be functioning on the Docker host.

The container does **not** provide the Linux kernel GPU driver.

The host should provide:

- Intel Arc-compatible GPU
- Linux `xe` driver
- `/dev/dri` render device
- Docker

Verify the GPU driver with:

```bash
lspci -nnk | grep -A4 -Ei 'Intel|VGA|Display'
```

A working Intel Arc GPU should show something similar to:

```text
Kernel driver in use: xe
Kernel modules: xe
```

## Finding Your Intel GPU Render Device

Intel GPUs appear under:

```text
/dev/dri/
```

List available render devices:

```bash
ls -la /dev/dri/
```

On systems with multiple GPUs, determine which render node belongs to which PCI device:

```bash
for r in /dev/dri/renderD*; do
    echo "=== $r ==="
    udevadm info -q property -n "$r" | grep -E "PCI_SLOT_NAME|DEVPATH"
    echo
done
```

Then compare the PCI address with:

```bash
lspci -nnk
```

For example, on the test system the Arc Pro B70 was:

```text
87:00.0 Intel Corporation Battlemage G31 [Arc Pro B70]
```

and mapped to:

```text
/dev/dri/renderD131
```

**Do not assume your GPU will use `renderD131`.**

Render device numbering varies between systems and may change when hardware configuration changes.

# Unraid Installation

## 1. Create Storage

It is recommended to create an Unraid share for AI models and generated content.

The included Unraid template defaults to a share named:

```text
AI
```

which produces paths such as:

```text
/mnt/user/AI/comfyui/models
/mnt/user/AI/comfyui/input
/mnt/user/AI/comfyui/output
```

You may use any share you prefer. Simply change the Host Path values during container installation.

Application configuration and custom nodes default to:

```text
/mnt/user/appdata/comfyui-intel-xpu/
```

## 2. GPU Device

Set the Intel GPU device to the appropriate render node for your system.

Example:

```text
/dev/dri/renderD131
```

## 3. Web Interface

The default ComfyUI port is:

```text
8188
```

Once running, access:

```text
http://UNRAID-IP:8188
```

The Unraid WebUI button should also open ComfyUI automatically.

# Docker CLI

Example:

```bash
docker run -d \
  --name comfyui-intel-xpu \
  --device=/dev/dri/renderD128:/dev/dri/renderD128 \
  --ipc=host \
  -p 8188:8188 \
  -v /path/to/config:/config \
  -v /path/to/custom_nodes:/custom_nodes \
  -v /path/to/models:/models \
  -v /path/to/input:/input \
  -v /path/to/output:/output \
  --restart unless-stopped \
  heroeswearkapes/comfyui-intel-xpu:latest
```

Replace:

```text
/dev/dri/renderD128
```

with the render device belonging to your Intel GPU.

# Docker Compose

Example:

```yaml
services:
  comfyui:
    image: heroeswearkapes/comfyui-intel-xpu:latest
    container_name: comfyui-intel-xpu

    devices:
      - /dev/dri/renderD128:/dev/dri/renderD128

    ports:
      - "8188:8188"

    volumes:
      - ./data/config:/config
      - ./data/models:/models
      - ./data/input:/input
      - ./data/output:/output
      - ./data/custom_nodes:/custom_nodes

    ipc: host

    restart: unless-stopped
```

# Model Directories

The container automatically creates common ComfyUI model directories on startup.

These include:

```text
/models/
├── checkpoints/
├── clip/
├── clip_vision/
├── configs/
├── controlnet/
├── diffusers/
├── diffusion_models/
├── embeddings/
├── gligen/
├── hypernetworks/
├── loras/
├── model_patches/
├── photomaker/
├── style_models/
├── text_encoders/
├── unet/
├── upscale_models/
├── vae/
└── vae_approx/
```

For example, normal checkpoint models can be placed in:

```text
/models/checkpoints/
```

On an Unraid installation using the recommended paths, that corresponds to:

```text
/mnt/user/AI/comfyui/models/checkpoints/
```

# Hugging Face

The official Hugging Face `hf` CLI is included.

Verify it with:

```bash
docker exec comfyui-intel-xpu hf --help
```

Models can be downloaded directly into persistent ComfyUI storage.

Example:

```bash
docker exec comfyui-intel-xpu \
  hf download stabilityai/stable-diffusion-xl-base-1.0 \
  sd_xl_base_1.0.safetensors \
  --local-dir /models/checkpoints
```

For gated or private models, provide a Hugging Face token using the `HF_TOKEN` environment variable or authenticate using the Hugging Face CLI.

**Never bake your Hugging Face token into the Docker image.**

# aria2

`aria2c` is included for fast, resumable downloads.

Verify:

```bash
docker exec comfyui-intel-xpu aria2c --version
```

Example:

```bash
docker exec comfyui-intel-xpu \
  aria2c \
  -c \
  -x 8 \
  -s 8 \
  -d /models/checkpoints \
  "MODEL_DOWNLOAD_URL"
```

# ComfyUI Manager

ComfyUI Manager is automatically installed into the persistent custom nodes directory:

```text
/custom_nodes/comfyui-manager
```

Because `/custom_nodes` is persistent, Manager and other custom nodes survive container upgrades and recreation.

Manager can be used to install and manage additional ComfyUI custom nodes.

## Updating ComfyUI

ComfyUI itself is intentionally managed by the Docker image.

You may see a message in Manager similar to:

```text
Your ComfyUI isn't git repo.
```

This is expected.

Do **not** use Manager to update the core ComfyUI installation inside this container.

Instead, update the Docker image:

```bash
docker pull heroeswearkapes/comfyui-intel-xpu:latest
```

and recreate/restart the container.

This keeps the application image reproducible and prevents container-local ComfyUI modifications from being lost during upgrades.

# Custom Node Compatibility

Not every ComfyUI custom node supports Intel XPU.

Custom nodes that explicitly require technologies such as:

- CUDA
- NVIDIA-specific libraries
- CUDA-only Triton kernels
- NVIDIA-specific Flash Attention implementations

may not function on Intel GPUs.

The core ComfyUI installation and standard PyTorch operations use native Intel XPU acceleration.

# Troubleshooting

## XPU is unavailable

Check the container log for:

```text
XPU available: True
```

If it reports:

```text
XPU available: False
```

first verify that the GPU device was passed into the container.

Example:

```bash
docker exec comfyui-intel-xpu ls -la /dev/dri
```

Then test PyTorch directly:

```bash
docker exec comfyui-intel-xpu python -c \
'import torch; print(torch.__version__); print(torch.xpu.is_available()); print(torch.xpu.device_count())'
```

## Permission Problems

Verify the render device exists on the host:

```bash
ls -l /dev/dri/renderD*
```

The Docker container must have access to the selected render device.

## View Logs

```bash
docker logs -f comfyui-intel-xpu
```

Successful Intel XPU initialization should resemble:

```text
XPU available: True
XPU device count: 1
Total VRAM 31023 MB
Device: xpu:0 Intel(R) Graphics
```

# Updating

Pull the latest image:

```bash
docker pull heroeswearkapes/comfyui-intel-xpu:latest
```

Then recreate the container using the same persistent volume mappings.

Unraid users can update through the normal Docker update mechanism.

# Versioning

The `latest` tag points to the current validated build.

Versioned releases use:

```text
YYYY.MM.DD-<ComfyUI commit>
```

This makes it possible to roll back to a known ComfyUI revision if an upstream change causes problems.

# Disclaimer

This is an independent community Docker image.

It is not an official ComfyUI, Intel, PyTorch, Hugging Face, or Unraid project.

Intel GPU and custom-node compatibility can vary by GPU generation, kernel, driver, PyTorch version, and individual workflow.

## License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for the full license text.