#!/usr/bin/env python3
"""Discard unused framebuffer alpha without changing the captured RGB pixels."""

import argparse
import os
import tempfile
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    raise SystemExit("PNG normalization requires Pillow in the host Python environment.")


def normalize(source: Path, destination: Path) -> None:
    with Image.open(source) as image:
        if image.format != "PNG":
            raise ValueError("capture is not a PNG")
        # Compositing would darken pixels whose framebuffer alpha is unused.
        opaque = image.convert("RGB")
    try:
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".png", delete=False) as output:
            temporary = Path(output.name)
        try:
            opaque.save(temporary, format="PNG")
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    finally:
        opaque.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    args = parser.parse_args()
    normalize(args.source, args.destination or args.source)


if __name__ == "__main__":
    main()
