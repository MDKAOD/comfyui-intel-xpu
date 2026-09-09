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
- Optional ComfyUI startup arguments through `CLI_ARGS`
- Optional runtime Python packages through `PIP_PACKAGES`

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

    environment:
      # Optional additional ComfyUI startup arguments
      # CLI_ARGS: "--disable-dynamic-vram --lowvram --cpu-vae --reserve-vram=1 --disable-smart-memory"

      # Optional additional Python packages
      # PIP_PACKAGES: "opencv-python imageio_ffmpeg"

    ipc: host

    restart: unless-stopped
```

## Optional Runtime Configuration

### Additional ComfyUI CLI Arguments

Additional ComfyUI command-line arguments can be supplied with the `CLI_ARGS` environment variable.

Example:

    CLI_ARGS=--disable-dynamic-vram --lowvram --cpu-vae --reserve-vram=1 --disable-smart-memory

The supplied arguments are appended to the standard ComfyUI launch command.

On Unraid, this option is available under **Advanced View** as **Additional ComfyUI CLI Arguments**.

Common options include:

| Argument | Description |
| --- | --- |
| `--lowvram` | Reduce VRAM usage by moving text encoders to CPU when DynamicVRAM is disabled. |
| `--novram` | More aggressive memory reduction when `--lowvram` is not enough. |
| `--cpu-vae` | Run the VAE on the CPU. |
| `--reserve-vram <GB>` | Reserve a specified amount of VRAM for the OS or other applications. |
| `--vram-headroom <GB>` | Keep additional VRAM free when using DynamicVRAM. |
| `--disable-dynamic-vram` | Disable DynamicVRAM and use estimate-based model loading. |
| `--enable-dynamic-vram` | Explicitly enable DynamicVRAM. |
| `--disable-smart-memory` | Aggressively offload models to system RAM instead of retaining them in VRAM. |
| `--highvram` | Keep models in GPU memory instead of unloading them to CPU memory. |
| `--gpu-only` | Store and run supported components on the GPU. |
| `--force-fp16` | Force FP16 operation. |
| `--force-fp32` | Force FP32 operation. |
| `--bf16-unet` | Run the diffusion model in BF16. |
| `--fp16-unet` | Run the diffusion model in FP16. |
| `--bf16-vae` | Run the VAE in BF16. |
| `--fp16-vae` | Run the VAE in FP16. |
| `--disable-pinned-memory` | Disable pinned system memory. |
| `--disable-mmap` | Disable mmap when loading safetensors. |
| `--mmap-torch-files` | Use mmap when loading checkpoint and PyTorch files. |
| `--force-non-blocking` | Force non-blocking operations where supported. |
| `--cache-none` | Minimize cache memory at the expense of additional node execution. |
| `--cache-classic` | Use the older aggressive caching behavior. |
| `--cache-lru <N>` | Use an LRU cache with up to N cached node results. |
| `--high-ram` | Prefer greater system RAM usage for caching/model loading. |
| `--fast-disk` | Prefer disk-backed dynamic loading/offloading over unpinned RAM. |

For the complete list of supported ComfyUI command-line arguments, see the [ComfyUI CLI Argument Reference](docs/comfyui-cli-arguments.md).

The available arguments depend on the version of ComfyUI included in the container. You can always view the exact options supported by your installed image with:

    docker exec ComfyUI-Intel-XPU python /opt/ComfyUI/main.py --help

### Additional Python Packages

Optional Python packages can be installed automatically at container startup using the `PIP_PACKAGES` environment variable.

Example:

    PIP_PACKAGES=opencv-python imageio_ffmpeg

Packages are installed into `/opt/venv`, the same Python environment used by ComfyUI, before ComfyUI Manager and ComfyUI start. Unset, empty, and whitespace-only values do nothing.

Arguments are parsed with Python's `shlex.split` and passed directly to pip in their original order. Pins, extras, direct URLs, Git URLs, requirements/constraints files, editable installs, local paths, and pip options remain supported wherever pip supports them. Quote arguments containing spaces; paths must exist inside the container. Shell variables, globs, and command substitutions inside the value are not expanded by the entrypoint.

Examples of environment variable values:

```text
PIP_PACKAGES="requests[socks]==2.32.4" imageio_ffmpeg
PIP_PACKAGES=-r /config/requirements.txt -c /config/constraints.txt
PIP_PACKAGES=-e "/custom_nodes/my local project"
```

These show literal values, not shell assignment commands. Use your deployment tool's quoting rules when configuring them.

On Unraid, this option is available under **Advanced View** as **Additional Python Packages**.

#### Restart, recreation, and caching

Pip runs on every startup with a nonempty package request. On an ordinary restart of the same container, installed packages remain in `/opt/venv`; pip normally leaves satisfied requirements alone. Options such as `--upgrade` or direct/local sources can require more work.

On container recreation, installed additions are lost and pip installs the requested packages against the image's environment again. Only downloaded artifacts and reusable built wheels are persisted, under:

```text
/config/pip-cache/v1/<runtime-key>/
```

Mount `/config` on persistent storage to retain this cache. Existing Compose and recommended Unraid appdata mappings already do this. No additional volume is required. Site-packages and virtual environments are not persisted, and there is no persistent success marker that can cause installation to be skipped.

The cache namespace combines an authoritative build-generated dependency identifier with cache schema version, Python implementation/version/SOABI, OS/architecture, and libc identity. During image build, after the base Python/XPU/ComfyUI dependencies are installed, the identifier snapshots their distribution versions and wheel-record hashes (including torch, torchvision, torchaudio, NumPy, pip and Intel packages), system-package versions, the interpreter, and system-package checksum manifests. Startup uses this saved digest; it does not rescan installed Python distributions or system packages, read wheel records, or probe the GPU. The image manifest stores only the schema and dependency digest, with no user request, credentials, or URLs.

The key represents the base image runtime: installing, upgrading, downgrading, or removing user packages does not change it. Changing `PIP_PACKAGES`, restarting, and recreating from the same image all retain the same namespace. A changed base dependency digest or interpreter/platform identity selects a different namespace. User compiler settings do not affect the key. This boundary does not certify arbitrary third-party wheels or track modifications to the container's base libraries. If you replace ABI-sensitive dependencies in the running container, change compiler targets, or change GPUs, bypass/purge the cache and rebuild affected packages as needed.

Caching reduces repeated download/build work; pip may still resolve dependencies, access package indexes, and install files. It does not guarantee offline startup. Large stable dependency stacks are better installed at build time in a derived image, especially when startup must perform no installation.

Caching is enabled only for the `PIP_PACKAGES` pip process. Image build steps and ComfyUI Manager retain their existing pip settings. The entrypoint logs the default cache path without echoing the package request. Explicit options in `PIP_PACKAGES`, including `--cache-dir /some/path` and `--no-cache-dir`, are passed after the default and can override it. An explicit custom cache path opts out of the automatic runtime separation; manage its compatibility yourself. The helper's default command-line cache path takes precedence over `PIP_CACHE_DIR` in the environment.

#### Refresh, removal, and recovery

Use pip's existing options as needed:

- `--upgrade`: select newer versions allowed by the request.
- `--force-reinstall`: reinstall even when the request is already satisfied.
- `--no-cache-dir`: bypass the cache. Combine with `--force-reinstall` for a fresh reinstall.

For example, a literal value is `PIP_PACKAGES=--force-reinstall --no-cache-dir imageio_ffmpeg`. Reinstalling unpinned packages may select newer versions and change dependencies, including components used by ComfyUI.

Removing a package from `PIP_PACKAGES` stops requesting it; it does not uninstall it from an existing container. Recreate the container to start from the image baseline and install the remaining request. Removed packages can still be present if included in the image or required by another package. Clearing the variable likewise does not uninstall anything.

If the runtime manifest is missing/invalid, runtime metadata cannot be read, or the default cache cannot be created/written, the helper warns and defaults to uncached installation. Explicit user cache options can still override that default. A pip failure stops startup, as before. Interrupted installations can leave partial changes in the container; retry, force-reinstall, or recreate it to recover. A corrupt cache can be bypassed or purged. No automatic rollback or destructive cache cleanup is performed.

#### Cache maintenance

Old runtime namespaces and artifacts can accumulate; there is no automatic eviction or size cap. Monitor appdata capacity or apply a filesystem quota. Use the actual namespace path printed in the startup log in place of `<runtime-key>`:

```bash
docker exec comfyui-intel-xpu du -sh /config/pip-cache
docker exec comfyui-intel-xpu python -m pip cache info --cache-dir "/config/pip-cache/v1/<runtime-key>"
docker exec comfyui-intel-xpu python -m pip cache purge --cache-dir "/config/pip-cache/v1/<runtime-key>"
```

Replace the placeholder before running these commands. The explicit `--cache-dir` selects the cache despite the image's global cache-disabling environment setting. Purging deletes cached artifacts, not installed packages; later installations may download/build them again. Avoid purging a namespace while an installation uses it. Unused older namespaces can be removed manually once no container uses them. Cache contents can generally be excluded from backups, but keep original local package sources and requirements files.

Use appdata/cache directories writable only by trusted users and containers. Package installation can execute build code, and pip or package build logs may contain user-supplied information even though the helper does not echo the request.

#### Testing the package helper

Run the GPU-free tests from the repository root:

```bash
python3 -B -m unittest discover -s tests -v
bash -n entrypoint.sh
```

The focused tests exercise argument preservation, cache identity and fallback, repeated startup/recreation invocation semantics, and startup failure propagation. Pip is mocked or replaced with a subprocess stub; these tests do not measure download savings or validate real dependency resolution, native wheel imports, or full-image XPU compatibility. Before release, build the image locally and verify actual restart/recreation installs, pip cache-option precedence, cache reuse, and a native extension. The repository does not establish arm64 image support; architecture separation is tested without claiming an arm64 XPU build.

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

## Acknowledgements

Special thanks to [MDKAOD](https://github.com/MDKAOD) for early community feedback and contributions to ComfyUI Intel XPU.

Their feature requests and pull request helped drive the addition of:

- Custom ComfyUI startup arguments through `CLI_ARGS`
- Optional runtime Python package installation through `PIP_PACKAGES`
- Improved runtime configurability for Docker and Unraid users

Thank you for taking the time to test the project, provide feedback, and contribute ideas and code back to the community.

## License

This project is licensed under the MIT License.

See the [LICENSE](LICENSE) file for the full license text.
