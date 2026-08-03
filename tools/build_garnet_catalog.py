"""Build Garnet ModelZoo release assets and a catalog-v1 document."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


MODELS = (
    ("Qwen3-VL-2B-Instruct", "vlm", "vl_2b_instruct"),
    ("Qwen3-1.7B", "text", "text_1_7b"),
    ("Qwen3-ASR-0.6B", "asr", "asr_0_6b"),
    ("Qwen3-TTS-12Hz-0.6B-CustomVoice", "tts", "tts_12hz_0_6b_custom_voice"),
    ("Qwen3-TTS-12Hz-1.7B-CustomVoice", "tts", "tts_12hz_1_7b_custom_voice"),
)
VERSION = "1.0.0"
BUFFER_SIZE = 8 * 1024 * 1024


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(BUFFER_SIZE), b""):
            digest.update(block)
    return digest.hexdigest()


def latest_snapshot(cache_root: Path, model_id: str) -> Path:
    root = cache_root / f"models--Qwen--{model_id}" / "snapshots"
    candidates = sorted(
        (path for path in root.iterdir() if path.is_dir()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    ) if root.is_dir() else []
    if not candidates:
        raise FileNotFoundError(f"No Hugging Face snapshot found under {root}")
    return candidates[0]


def source_files(snapshot: Path, xmodel_root: Path):
    for path in sorted(snapshot.rglob("*")):
        if path.is_file() and path.name not in {".gitattributes", "README.md"}:
            yield path, path.relative_to(snapshot).as_posix()
    for path in sorted(xmodel_root.rglob("*")):
        if (
            path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix != ".pyc"
            and not path.name.startswith("debug_")
        ):
            yield path, f"xmodel/{path.relative_to(xmodel_root).as_posix()}"


def is_weight(relative: str) -> bool:
    return relative.lower().endswith(".safetensors")


def safe_asset_name(relative: str, part_index: int, part_count: int) -> str:
    encoded = quote(relative, safe="._-").replace("%", "_")
    return f"{encoded}.part-{part_index:03d}-of-{part_count:03d}"


def write_parts(source: Path, asset_dir: Path, relative: str, part_size: int):
    size = source.stat().st_size
    part_count = max(1, (size + part_size - 1) // part_size)
    parts = []
    with source.open("rb") as input_stream:
        for index in range(1, part_count + 1):
            name = (
                quote(relative, safe="._-").replace("%", "_")
                if part_count == 1
                else safe_asset_name(relative, index, part_count)
            )
            output = asset_dir / name
            digest = hashlib.sha256()
            remaining = min(part_size, size - ((index - 1) * part_size))
            with output.open("wb") as output_stream:
                while remaining:
                    block = input_stream.read(min(BUFFER_SIZE, remaining))
                    if not block:
                        raise IOError(f"Unexpected EOF in {source}")
                    output_stream.write(block)
                    digest.update(block)
                    remaining -= len(block)
            parts.append((name, output.stat().st_size, digest.hexdigest()))
    return parts


def write_runtime_archive(entries, asset_dir: Path):
    archive_path = asset_dir / "xmodel.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_STORED) as archive:
        for source, relative in entries:
            archive.write(source, relative)
    return {
        "path": "xmodel.zip",
        "format": "zip",
        "size_bytes": archive_path.stat().st_size,
        "sha256": sha256(archive_path),
        "url": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--garnet-root", type=Path, required=True)
    parser.add_argument(
        "--hf-cache", type=Path,
        default=Path(os.environ.get("HF_HOME", Path.home() / ".cache/huggingface")) / "hub",
    )
    parser.add_argument("--output", type=Path, default=Path("dist"))
    parser.add_argument("--catalog", type=Path, default=Path("catalog/catalog-v1.json"))
    parser.add_argument("--repository", default="CantorAI/ModelZoo")
    parser.add_argument("--part-size-mib", type=int, default=1900)
    parser.add_argument("--model", action="append", choices=[item[0] for item in MODELS])
    args = parser.parse_args()

    selected = set(args.model or [item[0] for item in MODELS])
    part_size = args.part_size_mib * 1024 * 1024
    args.output.mkdir(parents=True, exist_ok=True)
    catalog_models = []

    for model_id, capability, xmodel_dir in MODELS:
        if model_id not in selected:
            continue
        snapshot = latest_snapshot(args.hf_cache, model_id)
        manifest_path = args.garnet_root / "xModel/qwen3" / xmodel_dir / "model.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        slug = manifest["slug"]
        tag = f"garnet/{capability}/{slug}/v{VERSION}"
        asset_dir = args.output / slug
        if asset_dir.exists():
            shutil.rmtree(asset_dir)
        asset_dir.mkdir(parents=True)
        entries = list(source_files(snapshot, manifest_path.parent))
        runtime_entries = [entry for entry in entries if not is_weight(entry[1])]
        archive = write_runtime_archive(runtime_entries, asset_dir)
        archive["url"] = (
            f"https://github.com/{args.repository}/releases/download/"
            f"{quote(tag, safe='/')}/xmodel.zip"
        )
        weights = []
        for source, relative in entries:
            if not is_weight(relative):
                continue
            size = source.stat().st_size
            if size == 0:
                continue
            complete_hash = sha256(source)
            built_parts = write_parts(source, asset_dir, relative, part_size)
            parts = []
            for name, part_bytes, part_hash in built_parts:
                url = (
                    f"https://github.com/{args.repository}/releases/download/"
                    # Keep tag separators literal. cpp-httplib follows GitHub's
                    # cross-host asset redirect correctly for slash tags, while
                    # an already escaped tag can be escaped a second time.
                    f"{quote(tag, safe='/')}/{quote(name, safe='._-')}"
                )
                parts.append({"url": url, "size_bytes": part_bytes, "sha256": part_hash})
            weights.append({
                "path": relative,
                "size_bytes": size,
                "sha256": complete_hash,
                "parts": parts,
            })
        release_manifest = {
            "schema_version": 1,
            "model_id": model_id,
            "version": VERSION,
            "tag": tag,
            "xmodel": archive,
            "weights": weights,
        }
        (asset_dir / "release-manifest.json").write_text(
            json.dumps(release_manifest, indent=2) + "\n",
            encoding="utf-8", newline="\n"
        )
        catalog_models.append({
            "id": model_id,
            "version": VERSION,
            "display_name": manifest["display_name"],
            "capability": capability,
            "runtime": {"minimum_version": "0.1.0"},
            "requirements": {"weights_bytes": sum(item["size_bytes"] for item in weights)},
            "license": {
                "spdx": "Apache-2.0",
                "upstream": f"https://huggingface.co/Qwen/{model_id}",
            },
            "release_tag": tag,
            "xmodel": archive,
            "weights": weights,
        })
        print(f"Prepared {model_id}: xmodel.zip + {len(weights)} weight files in {asset_dir}")

    catalog = {
        "schema_version": 1,
        "channel": "stable",
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "models": catalog_models,
    }
    args.catalog.parent.mkdir(parents=True, exist_ok=True)
    args.catalog.write_text(
        json.dumps(catalog, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"Wrote {args.catalog} with {len(catalog_models)} models")


if __name__ == "__main__":
    main()
