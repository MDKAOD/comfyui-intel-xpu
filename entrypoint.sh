#!/usr/bin/env bash

set -e

COMFYUI_DIR="${COMFYUI_DIR:-/opt/ComfyUI}"
COMFYUI_PORT="${COMFYUI_PORT:-8188}"

echo "=================================================="
echo " ComfyUI Intel XPU"
echo "=================================================="
echo

# ---------------------------------------------------------------------------
# Environment information
# ---------------------------------------------------------------------------

echo "[INFO] Python:"
python --version

echo
echo "[INFO] PyTorch:"
python - <<'PY'
import torch

print(f"PyTorch version: {torch.__version__}")
print(f"XPU support compiled: {hasattr(torch, 'xpu')}")

if hasattr(torch, "xpu"):
    try:
        available = torch.xpu.is_available()
        print(f"XPU available: {available}")

        if available:
            count = torch.xpu.device_count()
            print(f"XPU device count: {count}")

            for i in range(count):
                print(f"XPU {i}: {torch.xpu.get_device_name(i)}")
        else:
            print("[WARNING] No Intel XPU device is currently available.")

    except Exception as exc:
        print(f"[WARNING] Unable to initialize Intel XPU: {exc}")
PY

echo

# ---------------------------------------------------------------------------
# Check for Intel DRM devices
# ---------------------------------------------------------------------------

if [ -d /dev/dri ]; then
    echo "[INFO] /dev/dri devices:"
    ls -la /dev/dri
else
    echo "[WARNING] /dev/dri does not exist."
    echo "[WARNING] Intel GPU devices may not have been passed to the container."
fi

echo

# ---------------------------------------------------------------------------
# Initialize persistent ComfyUI directories
# ---------------------------------------------------------------------------

echo "[INFO] Initializing persistent directories..."

mkdir -p \
    /config \
    /models/checkpoints \
    /models/clip \
    /models/clip_vision \
    /models/configs \
    /models/controlnet \
    /models/diffusers \
    /models/diffusion_models \
    /models/embeddings \
    /models/gligen \
    /models/hypernetworks \
    /models/loras \
    /models/model_patches \
    /models/photomaker \
    /models/style_models \
    /models/text_encoders \
    /models/unet \
    /models/upscale_models \
    /models/vae \
    /models/vae_approx \
    /input \
    /output \
    /custom_nodes

echo "[INFO] Persistent directories ready."
echo

# ---------------------------------------------------------------------------
# ComfyUI Manager
# ---------------------------------------------------------------------------

MANAGER_DIR="/custom_nodes/comfyui-manager"

if [ ! -d "${MANAGER_DIR}/.git" ]; then
    echo "[INFO] ComfyUI Manager not found."
    echo "[INFO] Installing ComfyUI Manager..."

    rm -rf "${MANAGER_DIR}"

    git clone \
        --depth=1 \
        https://github.com/ltdrdata/ComfyUI-Manager.git \
        "${MANAGER_DIR}"

    if [ -f "${MANAGER_DIR}/requirements.txt" ]; then
        echo "[INFO] Installing ComfyUI Manager dependencies..."
        pip install -r "${MANAGER_DIR}/requirements.txt"
    fi

    echo "[INFO] ComfyUI Manager installed."
else
    echo "[INFO] ComfyUI Manager already installed."
fi

echo

# ---------------------------------------------------------------------------
# Start ComfyUI
# ---------------------------------------------------------------------------

if [ ! -f "${COMFYUI_DIR}/main.py" ]; then
    echo "[ERROR] ComfyUI main.py not found in ${COMFYUI_DIR}"
    exit 1
fi

echo "=================================================="
echo " Starting ComfyUI"
echo " Port: ${COMFYUI_PORT}"
echo "=================================================="
echo

cd "${COMFYUI_DIR}"

exec python main.py \
    --listen 0.0.0.0 \
    --port "${COMFYUI_PORT}" \
    "$@"