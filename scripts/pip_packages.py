"""Cache PIP_PACKAGES artifacts, never the installed application environment."""

import hashlib
from importlib import metadata
import json
import os
from pathlib import Path
import platform
import re
import shlex
import subprocess
import sys
import sysconfig
import tempfile


SCHEMA = 1
MANIFEST = Path("/opt/comfyui-runtime.json")
CACHE_ROOT = Path("/config/pip-cache")
REQUIRED_DISTRIBUTIONS = {"torch", "torchvision", "torchaudio", "numpy", "pip"}


def digest(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def file_digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def runtime_identity():
    """Collect stable interpreter/platform facts, never mutable package state."""
    soabi = sysconfig.get_config_var("SOABI")
    libc = platform.libc_ver()
    os_release = platform.freedesktop_os_release()
    if not soabi or not all(libc) or not platform.machine():
        raise ValueError("incomplete platform identity")
    return {
        "schema": SCHEMA,
        "python": [sys.implementation.name, sys.version, soabi],
        "platform": [sys.platform, platform.machine(), os_release["ID"],
                     os_release["VERSION_ID"]],
        "libc": libc,
    }


def base_dependency_identity():
    """Snapshot installed dependencies at image build time ONLY.

    RECORD hashes distinguish wheel builds with the same version. Include every
    distribution because native extensions may depend on more than torch/NumPy.
    Only hashes of file metadata are retained, never direct_url.json contents.
    Startup must use the saved digest, not scan this mutable environment again.
    """
    distributions = []
    for dist in metadata.distributions():
        name = re.sub(r"[-_.]+", "-", dist.metadata["Name"].lower())
        record = dist.read_text("RECORD")
        if not record or not dist.version:
            raise ValueError("incomplete distribution metadata")
        distributions.append((name, dist.version, digest(record)))
    if not REQUIRED_DISTRIBUTIONS.issubset(item[0] for item in distributions):
        raise ValueError("missing application runtime distributions")

    # The full dpkg inventory covers libc, libstdc++, Level Zero, OpenCL,
    # compiler libraries, and future Intel runtime packages without an allowlist.
    system_packages = subprocess.run(
        ["dpkg-query", "-W", "-f=${binary:Package}\t${Version}\t${Architecture}\t${db:Status-Status}\n"],
        check=True, capture_output=True, text=True, timeout=10,
    ).stdout.splitlines()
    if not system_packages:
        raise ValueError("missing system package inventory")
    return {
        **runtime_identity(),
        "distributions": sorted(distributions),
        "system_packages": digest(sorted(system_packages)),
    }


def write_manifest(path=MANIFEST):
    """Run after image dependency installation; identical inputs give one ID.

    Distribution RECORDs fingerprint Python artifacts (including torch builds).
    dpkg checksum manifests additionally distinguish native package builds.
    No user request or environment values are written to the image manifest.
    """
    try:
        checksums = sorted(Path("/var/lib/dpkg/info").glob("*.md5sums"))
        if not checksums:
            raise ValueError("missing system package checksums")
        generation = digest({
            "runtime": base_dependency_identity(),
            "interpreter": file_digest(Path(sys.executable).resolve()),
            "system_files": [(p.name, file_digest(p)) for p in checksums],
        })
    except Exception:
        # An unsupported dependency layout must not prevent otherwise valid
        # images from building. null deliberately fails runtime_key validation.
        generation = None
        print("[WARNING] Image dependency identity unavailable; default PIP_PACKAGES caching disabled.", flush=True)
    path.write_text(json.dumps({
        "schema": SCHEMA, "dependency_generation": generation,
    }, sort_keys=True) + "\n")


def runtime_key(manifest=MANIFEST):
    data = json.loads(manifest.read_text())
    if (not isinstance(data, dict) or data.get("schema") != SCHEMA
            or not isinstance(data.get("dependency_generation"), str)
            or not re.fullmatch(r"[0-9a-f]{64}", data["dependency_generation"])):
        raise ValueError("invalid image runtime manifest")
    return digest({
        "image": data["dependency_generation"],
        "runtime": runtime_identity(),
    })


def cache_options(manifest=MANIFEST, cache_root=CACHE_ROOT):
    try:
        key = runtime_key(manifest)
    except Exception:
        # Exception text may contain private paths or package metadata.
        print("[WARNING] Runtime identity unavailable; PIP_PACKAGES will run without caching.", flush=True)
        return ["--no-cache-dir"]
    cache = cache_root / f"v{SCHEMA}" / key
    try:
        cache.mkdir(mode=0o700, parents=True, exist_ok=True)
        # An actual write also detects read-only mounts, unlike mode checks.
        with tempfile.TemporaryFile(dir=cache) as probe:
            probe.write(b"cache probe")
            probe.flush()
    except OSError:
        print("[WARNING] Persistent pip cache unavailable; PIP_PACKAGES will run without caching.", flush=True)
        return ["--no-cache-dir"]
    print(f"[INFO] PIP_PACKAGES default cache: {cache} (user pip options may override)", flush=True)
    return ["--cache-dir", str(cache)]


def install_packages(specification=None, *, manifest=MANIFEST, cache_root=CACHE_ROOT):
    if specification is None:
        specification = os.environ.get("PIP_PACKAGES", "")
    try:
        packages = shlex.split(specification)
    except ValueError:
        print("[ERROR] Invalid quoting in PIP_PACKAGES.", flush=True)
        return 1
    if not packages:
        print("[INFO] No additional Python packages requested.", flush=True)
        return 0

    options = cache_options(manifest, cache_root)
    env = os.environ.copy()
    # Scope this override to the child; build steps and Manager retain the
    # image's global PIP_NO_CACHE_DIR=1. CLI user options remain last.
    env.pop("PIP_NO_CACHE_DIR", None)
    print("[INFO] Checking/installing additional Python packages...", flush=True)
    try:
        result = subprocess.run([
            sys.executable, "-m", "pip", "install",
            "--disable-pip-version-check", *options, *packages,
        ], env=env)
    except OSError:
        print("[ERROR] Unable to start pip for PIP_PACKAGES.", flush=True)
        return 1
    if result.returncode:
        # Avoid CalledProcessError's command repr, which would disclose arguments.
        print("[ERROR] PIP_PACKAGES installation failed; startup stopped.", flush=True)
        return result.returncode if result.returncode > 0 else 1
    print("[INFO] Additional Python package requirements processed.", flush=True)
    return 0


if __name__ == "__main__":
    if sys.argv[1:] == ["--write-runtime-manifest"]:
        write_manifest()
    elif sys.argv[1:]:
        sys.exit("Unsupported helper arguments")
    else:
        sys.exit(install_packages())
