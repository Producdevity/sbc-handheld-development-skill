#!/usr/bin/env python3
"""Discard unused framebuffer alpha without changing the captured RGB pixels."""

import argparse
import os
import struct
import tempfile
import zlib
from pathlib import Path

SIGNATURE = b"\x89PNG\r\n\x1a\n"


def chunks(data: bytes):
    position = len(SIGNATURE)
    while position < len(data):
        length = struct.unpack(">I", data[position:position + 4])[0]
        kind = data[position + 4:position + 8]
        yield kind, data[position + 8:position + 8 + length]
        position += 12 + length


def unfilter(raw: bytes, width: int, height: int, channels: int) -> list:
    stride = width * channels
    rows, previous, position = [], bytearray(stride), 0
    for _ in range(height):
        kind = raw[position]
        row = bytearray(raw[position + 1:position + 1 + stride])
        position += 1 + stride
        for i in range(stride):
            left = row[i - channels] if i >= channels else 0
            up = previous[i]
            corner = previous[i - channels] if i >= channels else 0
            if kind == 1:
                row[i] = (row[i] + left) & 255
            elif kind == 2:
                row[i] = (row[i] + up) & 255
            elif kind == 3:
                row[i] = (row[i] + (left + up) // 2) & 255
            elif kind == 4:
                estimate = left + up - corner
                a, b, c = abs(estimate - left), abs(estimate - up), abs(estimate - corner)
                row[i] = (row[i] + (left if a <= b and a <= c else up if b <= c else corner)) & 255
            elif kind != 0:
                raise ValueError(f"unknown PNG filter {kind}")
        rows.append(row)
        previous = row
    return rows


def chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def normalize(source: Path, destination: Path) -> None:
    data = source.read_bytes()
    if not data.startswith(SIGNATURE):
        raise ValueError("capture is not a PNG")
    parts = list(chunks(data))
    width, height, depth, color, _, _, interlace = struct.unpack(">IIBBBBB", parts[0][1])
    # fbgrab and FFmpeg write 8-bit, non-interlaced RGB or RGBA.
    if depth != 8 or color not in (2, 6) or interlace:
        raise ValueError("unsupported PNG layout; expected 8-bit non-interlaced RGB or RGBA")
    channels = 4 if color == 6 else 3
    rows = unfilter(zlib.decompress(b"".join(body for kind, body in parts if kind == b"IDAT")), width, height, channels)
    # Dropping alpha keeps RGB as captured; compositing would darken pixels whose alpha is unused.
    pixels = b"".join(b"\0" + (bytes(row) if channels == 3 else bytes(b for i, b in enumerate(row) if i % 4 != 3))
                      for row in rows)
    png = (SIGNATURE + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(pixels, 6)) + chunk(b"IEND", b""))
    with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=".png", delete=False) as output:
        temporary = Path(output.name)
        output.write(png)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path, nargs="?")
    args = parser.parse_args()
    normalize(args.source, args.destination or args.source)


if __name__ == "__main__":
    main()
