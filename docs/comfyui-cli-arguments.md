# ComfyUI CLI Argument Reference

This document describes the optional command-line arguments available to **ComfyUI Intel XPU** through the `CLI_ARGS` environment variable.

These arguments are passed directly to ComfyUI when the container starts.

> **Important:** Available arguments can change when the ComfyUI version included in the Docker image is updated. This document reflects the ComfyUI CLI available in the currently validated container build.

## Using CLI_ARGS

### Unraid

Enable **Advanced View** when editing the container and enter additional arguments in:

    Additional ComfyUI CLI Arguments

Example:

    --disable-dynamic-vram --lowvram --cpu-vae --reserve-vram=1 --disable-smart-memory

### Docker

Pass the `CLI_ARGS` environment variable:

    -e 'CLI_ARGS=--disable-dynamic-vram --reserve-vram=1'

### Docker Compose

    environment:
      CLI_ARGS: "--disable-dynamic-vram --reserve-vram=1"

## Verify Available Arguments

The exact CLI supported by your installed image can always be displayed with:

    docker exec comfyui-intel-xpu python /opt/ComfyUI/main.py --help

---

# Server and Networking

| Argument | Value | Description |
| --- | --- | --- |
| `--listen` | `[IP]` | IP address or addresses ComfyUI should listen on. The container already configures ComfyUI to listen on `0.0.0.0`. |
| `--port` | `PORT` | ComfyUI listening port. The container normally manages this automatically. |
| `--tls-keyfile` | `FILE` | Path to a TLS/SSL private key. Requires `--tls-certfile`. |
| `--tls-certfile` | `FILE` | Path to a TLS/SSL certificate. Requires `--tls-keyfile`. |
| `--enable-cors-header` | `[ORIGIN]` | Enable CORS, optionally restricted to a specific origin. |
| `--max-upload-size` | `MB` | Maximum allowed upload size in megabytes. |
| `--enable-compress-response-body` | — | Enable HTTP response-body compression. |
| `--comfy-api-base` | `URL` | Override the base URL used for the ComfyUI API. |

> The container already supplies `--listen` and `--port`. Overriding these with `CLI_ARGS` is generally unnecessary.

---

# Directory and Storage Options

| Argument | Value | Description |
| --- | --- | --- |
| `--base-directory` | `PATH` | Set the base directory used for models, custom nodes, input, output, temp, and user directories. |
| `--extra-model-paths-config` | `PATH [PATH ...]` | Load one or more `extra_model_paths.yaml` files. |
| `--output-directory` | `PATH` | Override the ComfyUI output directory. |
| `--temp-directory` | `PATH` | Override the temporary directory. |
| `--input-directory` | `PATH` | Override the ComfyUI input directory. |
| `--user-directory` | `PATH` | Override the ComfyUI user directory. |
| `--models-directory` | `PATH` | Override the ComfyUI models directory. |

The Docker container already provides persistent mappings for the standard models, input, output, configuration, and custom-node directories. Override these only when you understand how they interact with the container's volume mappings.

---

# Device Selection

| Argument | Value | Description |
| --- | --- | --- |
| `--cuda-device` | `DEVICE_ID` | Select CUDA device IDs. Intended for CUDA systems and generally not applicable to this Intel XPU image. |
| `--default-device` | `DEVICE_ID` | Select the default device while leaving other visible devices available. |
| `--directml` | `[DEVICE]` | Use Torch DirectML. |
| `--oneapi-device-selector` | `SELECTOR_STRING` | Set the oneAPI device selector used by ComfyUI. |
| `--supports-fp8-compute` | — | Tell ComfyUI to treat the device as supporting FP8 compute. |

For normal Intel Arc use, Docker device passthrough should be configured using the appropriate `/dev/dri/renderD###` device.

---

# Model and GPU Memory Management

These options are particularly useful on systems with limited VRAM or when running other GPU workloads alongside ComfyUI.

| Argument | Value | Description |
| --- | --- | --- |
| `--gpu-only` | — | Store and run supported components on the GPU. |
| `--highvram` | — | Keep models in GPU memory instead of unloading them to system memory after use. |
| `--lowvram` | — | Reduce VRAM usage. When DynamicVRAM is disabled, text encoders are moved to CPU. |
| `--novram` | — | More aggressive memory reduction when `--lowvram` is insufficient. |
| `--cpu` | — | Run everything on CPU. Very slow for normal image-generation workloads. |
| `--cpu-vae` | — | Run the VAE on CPU. |
| `--reserve-vram` | `GB` | Reserve the specified amount of VRAM for the operating system or other applications. |
| `--vram-headroom` | `GB` | Ask DynamicVRAM to maintain additional completely unused VRAM. |
| `--disable-nvml-pressure` | — | Use CUDA instead of NVML for DynamicVRAM memory-pressure handling. Primarily relevant to NVIDIA systems. |
| `--async-offload` | `[NUM_STREAMS]` | Enable asynchronous weight offloading. Optional value controls the number of streams. |
| `--disable-async-offload` | — | Disable asynchronous weight offloading. |
| `--disable-dynamic-vram` | — | Disable DynamicVRAM and use estimate-based model loading. |
| `--enable-dynamic-vram` | — | Explicitly enable DynamicVRAM. |
| `--disable-smart-memory` | — | Aggressively offload models to system RAM instead of keeping them in VRAM when possible. |
| `--disable-pinned-memory` | — | Disable pinned system memory. |
| `--high-ram` | — | Prefer greater system RAM usage where it may improve performance. |
| `--fast-disk` | — | Prefer disk-backed dynamic loading/offloading over unpinned RAM. |

Example for reducing GPU memory usage:

    CLI_ARGS=--disable-dynamic-vram --lowvram --cpu-vae --reserve-vram=1 --disable-smart-memory

---

# Precision

## General Precision

| Argument | Description |
| --- | --- |
| `--force-fp32` | Force FP32 operation. |
| `--force-fp16` | Force FP16 operation. |
| `--fp16-intermediates` | Experimental: use FP16 for intermediate tensors between nodes instead of FP32. |

## Diffusion Model / UNet Precision

| Argument | Description |
| --- | --- |
| `--fp32-unet` | Run the diffusion model in FP32. |
| `--fp64-unet` | Run the diffusion model in FP64. |
| `--bf16-unet` | Run the diffusion model in BF16. |
| `--fp16-unet` | Run the diffusion model in FP16. |
| `--fp8_e4m3fn-unet` | Store UNet weights using FP8 E4M3FN. |
| `--fp8_e5m2-unet` | Store UNet weights using FP8 E5M2. |
| `--fp8_e8m0fnu-unet` | Store UNet weights using FP8 E8M0FNU. |

## VAE Precision

| Argument | Description |
| --- | --- |
| `--fp16-vae` | Run the VAE in FP16. May cause black images with incompatible models/devices. |
| `--fp32-vae` | Run the VAE in FP32. |
| `--bf16-vae` | Run the VAE in BF16. |
| `--cpu-vae` | Run the VAE on CPU. |

## Text Encoder Precision

| Argument | Description |
| --- | --- |
| `--fp8_e4m3fn-text-enc` | Store text-encoder weights using FP8 E4M3FN. |
| `--fp8_e5m2-text-enc` | Store text-encoder weights using FP8 E5M2. |
| `--fp16-text-enc` | Store text-encoder weights using FP16. |
| `--fp32-text-enc` | Store text-encoder weights using FP32. |
| `--bf16-text-enc` | Store text-encoder weights using BF16. |

Precision support depends on the GPU, PyTorch XPU implementation, model, and individual workflow.

---

# Attention and Compute Backends

| Argument | Description |
| --- | --- |
| `--use-split-cross-attention` | Use split cross-attention optimization. |
| `--use-quad-cross-attention` | Use sub-quadratic cross-attention optimization. |
| `--use-pytorch-cross-attention` | Use PyTorch scaled-dot-product/cross-attention functionality. |
| `--use-sage-attention` | Use Sage Attention when available. |
| `--use-flash-attention` | Use FlashAttention when available. |
| `--use-ck-attention` | Use Comfy Kitchen attention. |
| `--disable-xformers` | Disable xFormers. |
| `--force-upcast-attention` | Force attention upcasting. |
| `--dont-upcast-attention` | Disable attention upcasting. |
| `--enable-triton-backend` | Enable the Comfy Kitchen Triton backend. |
| `--disable-triton-backend` | Force-disable the Comfy Kitchen Triton backend. |

> Some attention implementations are CUDA/NVIDIA-specific or may not support Intel XPU. Availability depends on the installed runtime and custom nodes.

---

# CUDA-Specific Options

The following options are exposed by upstream ComfyUI but are generally **not applicable to this Intel XPU image**.

| Argument | Description |
| --- | --- |
| `--cuda-device` | Select CUDA devices. |
| `--cuda-malloc` | Enable `cudaMallocAsync`. |
| `--disable-cuda-malloc` | Disable `cudaMallocAsync`. |
| `--disable-cuda-graphs` | Disable CUDA graphs. |
| `--disable-nvml-pressure` | Avoid NVML for DynamicVRAM pressure handling. |

---

# Preview Options

| Argument | Value | Description |
| --- | --- | --- |
| `--preview-method` | `[none,auto,latent2rgb,taesd]` | Select the sampler preview method. |
| `--preview-size` | `SIZE` | Set the maximum sampler preview size. |

---

# Caching

| Argument | Value | Description |
| --- | --- | --- |
| `--cache-ram` | `[GB ...]` | Use RAM-pressure caching with optional headroom thresholds. |
| `--cache-classic` | — | Use the older aggressive caching behavior. |
| `--cache-lru` | `N` | Cache up to N node results using LRU caching. |
| `--cache-none` | — | Disable node-result caching, reducing memory usage at the cost of additional execution. |
| `--high-ram` | — | Prefer greater RAM usage where appropriate. |

---

# Performance and Memory-Mapping Options

| Argument | Description |
| --- | --- |
| `--force-channels-last` | Force channels-last tensor format when performing inference. |
| `--force-non-blocking` | Force non-blocking operations where applicable. May improve performance on some non-NVIDIA systems. |
| `--mmap-torch-files` | Use mmap when loading checkpoint/PT files. |
| `--disable-mmap` | Disable mmap when loading safetensors. |
| `--fast-disk` | Prefer disk-backed dynamic loading/offloading. |
| `--deterministic` | Prefer deterministic PyTorch algorithms where possible, potentially reducing performance. |

---

# Experimental Fast Optimizations

    --fast [FAST ...]

Enables experimental optimizations.

Running:

    --fast

without arguments enables all currently available fast optimizations.

The current ComfyUI build reports these available optimizations:

- `fp16_accumulation`
- `fp8_matrix_mult`
- `cublas_ops`
- `autotune`

Specific optimizations can be selected individually.

Example:

    CLI_ARGS=--fast fp16_accumulation

> These optimizations are experimental and may cause crashes or reduced output quality. Some options, such as `cublas_ops`, are CUDA-specific and not applicable to Intel XPU.

---

# ComfyUI Manager

| Argument | Description |
| --- | --- |
| `--enable-manager` | Enable ComfyUI Manager functionality. |
| `--disable-manager-ui` | Disable the Manager UI/endpoints while allowing background Manager tasks. |
| `--enable-manager-legacy-ui` | Enable the legacy Manager UI. Also enables Manager. |

ComfyUI Manager is already installed automatically by this container.

---

# Custom Nodes and API Nodes

| Argument | Value | Description |
| --- | --- | --- |
| `--disable-all-custom-nodes` | — | Disable all custom nodes. |
| `--whitelist-custom-nodes` | `NODE [NODE ...]` | Allow specific custom-node folders when all other custom nodes are disabled. |
| `--disable-api-nodes` | — | Disable API nodes and prevent the frontend from communicating with the internet. |

---

# Frontend Options

| Argument | Value | Description |
| --- | --- | --- |
| `--auto-launch` | — | Automatically open ComfyUI in the default browser. |
| `--disable-auto-launch` | — | Disable automatic browser launch. |
| `--front-end-version` | `OWNER/REPO@VERSION` | Select and download a specific ComfyUI frontend implementation/version. |
| `--front-end-root` | `PATH` | Use a local frontend directory instead of downloading one. |
| `--enable-compress-response-body` | — | Enable compressed HTTP responses. |

---

# User and Multi-User Options

| Argument | Description |
| --- | --- |
| `--multi-user` | Enable per-user storage. |
| `--user-directory` | Override the user-directory path. |

---

# Logging and Diagnostics

| Argument | Value | Description |
| --- | --- | --- |
| `--verbose` | `[LEVEL FILE ...]` | Configure console or file logging. Can be specified multiple times. |
| `--log-stdout` | — | Send normal process output to stdout instead of stderr. |
| `--dont-print-server` | — | Suppress normal server output. |
| `--debug-hang` | — | Enable stack-trace dumps when Ctrl+C is used for debugging hangs. |
| `--quick-test-for-ci` | — | Run ComfyUI's quick CI test mode. |

---

# Metadata

| Argument | Description |
| --- | --- |
| `--disable-metadata` | Disable saving prompt metadata into generated files. |

---

# Database and Assets

| Argument | Value | Description |
| --- | --- | --- |
| `--database-url` | `URL` | Configure the database URL used by ComfyUI. |
| `--enable-assets` | — | Enable the ComfyUI assets system. |
| `--enable-asset-hashing` | — | Calculate BLAKE3 content hashes while scanning assets. |

Asset hashing can improve future asset portability and deduplication features but adds startup and output-processing overhead.

---

# Feature Flags

## Set Feature Flags

    --feature-flag KEY[=VALUE]

Sets a ComfyUI server feature flag.

Examples:

    --feature-flag show_signin_button=true

or:

    --feature-flag some_feature

The option can be specified multiple times.

## List Available Feature Flags

    --list-feature-flags

Prints the currently registered CLI-settable feature flags as JSON and exits.

---

# Windows Standalone Option

| Argument | Description |
| --- | --- |
| `--windows-standalone-build` | Enable conveniences intended for the Windows standalone ComfyUI build. Not applicable to this Linux Docker image. |

---

# Additional Notes for Intel XPU

Not every upstream ComfyUI argument is necessarily useful or supported on Intel GPUs.

In particular, options related specifically to:

- CUDA
- NVIDIA NVML
- CUDA graphs
- CUDA malloc
- NVIDIA-specific attention implementations
- CUDA-specific experimental optimizations

may not function with Intel XPU.

The availability and usefulness of other options can depend on:

- Intel GPU generation
- Linux kernel
- `xe` driver version
- Intel Level Zero runtime
- PyTorch XPU version
- ComfyUI version
- model
- custom nodes
- workflow

If ComfyUI fails to start after adding custom arguments, remove `CLI_ARGS` and confirm the container starts normally before adding options back individually.

---

# Getting the Current CLI Reference

Because ComfyUI is updated regularly, the running container is always the authoritative source for its supported command-line arguments.

Run:

    docker exec comfyui-intel-xpu python /opt/ComfyUI/main.py --help

If an argument documented here is no longer shown by the installed version of ComfyUI, follow the output from the running container.