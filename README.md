# CantorAI ModelZoo

ModelZoo is the public artifact registry for models supported by the CantorAI
Garnet runtime. The Git repository contains manifests and packaging tools;
large weight files are GitHub Release assets and are never committed to Git.

## Garnet catalog

GitHub Release assets are flat. ModelZoo supplies hierarchy through signed
catalog metadata:

- release tag: `garnet/<capability>/<model-slug>/v<version>`
- catalog category: `text`, `vlm`, `asr`, or `tts`
- `xmodel`: one `xmodel.zip` containing model metadata and the complete
  `xmodel/` folder
- `weights`: only `.safetensors` files, split into numbered parts only when
  they exceed the GitHub asset threshold

The current catalog covers Qwen3 text, VLM, ASR, and both CustomVoice TTS
models. Garnet downloads with range resume, verifies `xmodel.zip` and every
weight part, extracts the metadata/XModel archive, reconstructs split weights,
and verifies each complete SHA-256 digest.

Use `tools/build_garnet_catalog.py --help` to prepare assets and
`tools/sign_catalog.py --help` to create the detached Ed25519 signature.

## Licensing

Catalog metadata and repository tooling are Apache-2.0. Every model entry
retains its upstream license and attribution. Garnet runtime binaries have a
separate CantorAI evaluation/commercial license.
