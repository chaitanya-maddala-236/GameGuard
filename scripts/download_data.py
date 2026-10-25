"""Download the public, licensed RE4 telemetry split from Hugging Face."""

from __future__ import annotations

import hashlib
from pathlib import Path

import requests

URL = "https://huggingface.co/datasets/rmems/gaming-telemetry/resolve/main/re4/train-00000.parquet"
DESTINATION = Path("data/raw/re4/train-00000.parquet")


def main() -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    response = requests.get(URL, timeout=(10, 120), allow_redirects=True)
    response.raise_for_status()
    DESTINATION.write_bytes(response.content)
    digest = hashlib.sha256(response.content).hexdigest()
    print(f"Downloaded {len(response.content):,} bytes to {DESTINATION}")
    print(f"SHA-256: {digest}")


if __name__ == "__main__":
    main()
