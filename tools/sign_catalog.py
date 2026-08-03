"""Sign a Garnet catalog with an Ed25519 PEM private key."""

from __future__ import annotations

import argparse
import base64
from pathlib import Path

from cryptography.hazmat.primitives import serialization



def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--private-key", type=Path, required=True)
    parser.add_argument("--signature", type=Path)
    args = parser.parse_args()
    output = args.signature or args.catalog.with_suffix(args.catalog.suffix + ".sig")
    private_key = serialization.load_pem_private_key(
        args.private_key.read_bytes(), password=None
    )
    signature = private_key.sign(args.catalog.read_bytes())
    encoded = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    output.write_text(encoded + "\n", encoding="ascii", newline="\n")
    print(f"Wrote {output}")


if __name__ == "__main__":
    main()
