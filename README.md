# CantorAI ModelZoo 🦓

This repository is the central hub for hosting pre-trained models, optimized weights, and AI assets used across the CantorAI ecosystem. 

Because many models require massive data files (often exceeding GitHub's 100MB file limit), the core repository acts as a lightweight index. The actual model binaries are distributed as packaged archives on the **[Releases](../../releases)** page.

## 📦 Getting Started

To download models for deployment:
1. Navigate to the [Releases](../../releases) page.
2. Download the ZIP or TAR archive for the specific model suite you need (e.g., `xworld_onnx_models_small_v1.zip`).
3. Extract the contents directly into your application's `models/` directory.

## ⚙️ Model Formats

The ModelZoo hosts various architectures tailored for different deployment targets:
- **`.onnx`**: Framework-agnostic graphs ready to be compiled into hardware-specific TensorRT `.engine` files.
- **`.pth` / `.pt`**: Native PyTorch checkpoints for fine-tuning or direct inference.
- **`.safetensors`**: Secure, fast-loading weight formats for Large Language Models.

## ⚖️ Licensing

Models hosted in this repository are converted or fine-tuned from open-source baselines. Unless otherwise specified in a specific release, the models are distributed under the permissive **[Apache 2.0 License](LICENSE)**.

When using these models, please respect the original licenses of the foundational architectures (e.g., Google SigLIP, Megvii YOLOX, Qwen, etc.).
