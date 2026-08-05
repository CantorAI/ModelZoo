"""Build a stored-ZIP NVIDIA acceleration pack and catalog entry.

The tool deliberately requires an approved redistribution-license file. It
does not publish anything; release upload and catalog signing remain separate
publisher actions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
import zipfile
from pathlib import Path


SM_RESOURCES = {
    "75": "nvinfer_builder_resource_sm75_10.dll",
    "80": "nvinfer_builder_resource_sm80_10.dll",
    "86": "nvinfer_builder_resource_sm86_10.dll",
    "89": "nvinfer_builder_resource_sm89_10.dll",
    "90": "nvinfer_builder_resource_sm90_10.dll",
    "100": "nvinfer_builder_resource_sm100_10.dll",
    "120": "nvinfer_builder_resource_sm120_10.dll",
}

CUDA_FILES = [
    "cudart64_13.dll",
    "cublasLt64_13.dll",
    "cublas64_13.dll",
    "nppc64_13.dll",
    "nppig64_13.dll",
    "nvjpeg64_13.dll",
]
TENSORRT_FILES = [
    "nvinfer_10.dll",
    "nvinfer_plugin_10.dll",
    "nvinfer_builder_resource_ptx_10.dll",
]
LOAD_ORDER = [
    "bin/cudart64_13.dll",
    "bin/cublasLt64_13.dll",
    "bin/cublas64_13.dll",
    "bin/nppc64_13.dll",
    "bin/nppig64_13.dll",
    "bin/nvjpeg64_13.dll",
    "bin/nvinfer_10.dll",
    "bin/nvinfer_plugin_10.dll",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require_file(root: Path, name: str) -> Path:
    candidate = root / name
    if not candidate.is_file():
        raise FileNotFoundError(candidate)
    return candidate


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--sm", choices=sorted(SM_RESOURCES), required=True)
    parser.add_argument("--compute-capability", action="append", required=True)
    parser.add_argument("--minimum-driver-api", type=int, required=True)
    parser.add_argument("--priority", type=int, default=0)
    parser.add_argument("--cuda-bin", type=Path, required=True)
    parser.add_argument("--tensorrt-bin", type=Path, required=True)
    parser.add_argument(
        "--redistribution-license",
        type=Path,
        action="append",
        required=True,
        help="Approved NVIDIA license/notice file; repeat for CUDA and TensorRT",
    )
    parser.add_argument("--release-base-url", required=True)
    parser.add_argument("--output", type=Path, default=Path("dist/acceleration"))
    args = parser.parse_args()

    license_paths = [path.resolve() for path in args.redistribution_license]
    for license_path in license_paths:
        if not license_path.is_file():
            raise FileNotFoundError(license_path)
    package_id = f"nvidia-windows-x64-cuda13.2-trt10-sm{args.sm}"
    args.output.mkdir(parents=True, exist_ok=True)
    archive = args.output / f"{package_id}-{args.version}.zip"

    with tempfile.TemporaryDirectory(prefix="garnet-acceleration-") as temporary:
        root = Path(temporary)
        binary = root / "bin"
        binary.mkdir()
        for name in CUDA_FILES:
            shutil.copy2(require_file(args.cuda_bin, name), binary / name)
        resource = SM_RESOURCES[args.sm]
        for name in [*TENSORRT_FILES, resource]:
            shutil.copy2(require_file(args.tensorrt_bin, name), binary / name)
        notices = root / "licenses"
        notices.mkdir()
        for index, license_path in enumerate(license_paths, start=1):
            shutil.copy2(
                license_path,
                notices / f"{index:02d}-{license_path.name}",
            )
        with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED) as bundle:
            for file in sorted(root.rglob("*")):
                if file.is_file():
                    bundle.write(file, file.relative_to(root).as_posix())

    release_base = args.release_base_url.rstrip("/")
    entry = {
        "id": package_id,
        "version": args.version,
        "display_name": f"NVIDIA CUDA 13.2 / TensorRT 10 (SM {args.sm})",
        "capability": "acceleration",
        "acceleration": {
            "vendor": "nvidia",
            "platforms": ["windows-x64"],
            "minimum_driver_api": args.minimum_driver_api,
            "priority": args.priority,
            "compute_capabilities": args.compute_capability,
            "cuda": "13.2",
            "tensorrt": "10",
        },
        "runtime": {
            "path": "runtime.zip",
            "format": "zip",
            "size_bytes": archive.stat().st_size,
            "sha256": sha256(archive),
            "url": f"{release_base}/{archive.name}",
        },
        "runtime_libraries": LOAD_ORDER,
    }
    entry_path = args.output / f"{package_id}-{args.version}.catalog-entry.json"
    entry_path.write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
    print(archive)
    print(entry_path)


if __name__ == "__main__":
    main()
