# syntax=docker/dockerfile:1

ARG UBUNTU_VERSION=26.04
FROM ubuntu:${UBUNTU_VERSION}

LABEL org.opencontainers.image.title="ComfyUI Intel XPU"
LABEL org.opencontainers.image.description="ComfyUI container with native PyTorch XPU support for Intel Arc GPUs"
LABEL org.opencontainers.image.licenses="MIT"

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    COMFYUI_DIR=/opt/ComfyUI \
    COMFYUI_PORT=8188

# ---------------------------------------------------------------------------
# Base dependencies
# ---------------------------------------------------------------------------

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    git \
    python3 \
    python3-pip \
    python3-venv \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    libze1 \
    libze-intel-gpu1 \
    intel-opencl-icd \
    intel-ocloc \
    libigc2 \
    aria2 \
    unzip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Python virtual environment
# ---------------------------------------------------------------------------

RUN python3 -m venv /opt/venv

ENV PATH="/opt/venv/bin:${PATH}"

RUN pip install --upgrade \
    pip \
    setuptools \
    wheel

# ---------------------------------------------------------------------------
# Quality-of-life tooling
# ---------------------------------------------------------------------------

RUN pip install \
    huggingface_hub \
    OpenCV-python \
    imageio_ffmpeg

# ---------------------------------------------------------------------------
# PyTorch XPU
#
# Native Intel GPU support.
# We are intentionally NOT using legacy Intel Extension for PyTorch / IPEX.
# ---------------------------------------------------------------------------

RUN pip install \
    torch \
    torchvision \
    torchaudio \
    --index-url https://download.pytorch.org/whl/xpu

# ---------------------------------------------------------------------------
# ComfyUI
#
# COMFYUI_COMMIT can be supplied by the update script to produce a
# reproducible image containing an exact upstream ComfyUI revision.
#
# If COMFYUI_COMMIT is not supplied, the current upstream master branch
# will be used for manual/development builds.
# ---------------------------------------------------------------------------

ARG COMFYUI_COMMIT=""

RUN git clone \
    https://github.com/Comfy-Org/ComfyUI.git \
    ${COMFYUI_DIR} \
    && cd ${COMFYUI_DIR} \
    && if [ -n "${COMFYUI_COMMIT}" ]; then \
         echo "Checking out ComfyUI commit ${COMFYUI_COMMIT}" && \
         git checkout "${COMFYUI_COMMIT}"; \
       else \
         echo "No COMFYUI_COMMIT supplied; using current upstream HEAD"; \
       fi \
    && rm -rf .git

WORKDIR ${COMFYUI_DIR}

RUN pip install -r requirements.txt

# ---------------------------------------------------------------------------
# Persistent data directories
#
# External Docker/Unraid volumes mount here.
# ComfyUI's native directories are symlinked to these locations.
# ---------------------------------------------------------------------------

RUN mkdir -p \
    /config \
    /models \
    /input \
    /output \
    /custom_nodes \
    && rm -rf \
        ${COMFYUI_DIR}/models \
        ${COMFYUI_DIR}/input \
        ${COMFYUI_DIR}/output \
        ${COMFYUI_DIR}/custom_nodes \
    && ln -s /models ${COMFYUI_DIR}/models \
    && ln -s /input ${COMFYUI_DIR}/input \
    && ln -s /output ${COMFYUI_DIR}/output \
    && ln -s /custom_nodes ${COMFYUI_DIR}/custom_nodes

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

COPY entrypoint.sh /entrypoint.sh

RUN chmod +x /entrypoint.sh

# ---------------------------------------------------------------------------
# Networking
# ---------------------------------------------------------------------------

EXPOSE 8188

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

ENTRYPOINT ["/entrypoint.sh"]
