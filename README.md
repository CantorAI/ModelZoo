# CantorAI ModelZoo

ModelZoo is the public artifact registry for models supported by the CantorAI
Garnet runtime. The Git repository contains manifests and packaging tools;
large weight files are GitHub Release assets and are never committed to Git.

## Garnet catalog

GitHub Release assets are flat. ModelZoo supplies hierarchy through signed
catalog metadata:

- release tag: `garnet/<capability>/<model-slug>/v<version>`
- catalog category: `text`, `vlm`, `asr`, or `tts`
- file paths: reconstructed by Garnet from each asset or split asset set

The current catalog covers Qwen3 text, VLM, ASR, and both CustomVoice TTS
models. Files larger than GitHub's 2 GiB asset limit are split into numbered
parts; Garnet downloads with range resume, verifies every part, reconstructs
the original file, and verifies its complete SHA-256 digest.

Use `tools/build_garnet_catalog.py --help` to prepare assets and
`tools/sign_catalog.py --help` to create the detached Ed25519 signature.

## Licensing

Catalog metadata and repository tooling are Apache-2.0. Every model entry
retains its upstream license and attribution. Garnet runtime binaries have a
separate CantorAI evaluation/commercial license.
