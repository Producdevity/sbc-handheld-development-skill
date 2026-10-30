import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
import zlib


SKILL_ROOT = Path(__file__).resolve().parents[1]
CAPTURE_SCREEN = SKILL_ROOT / "scripts" / "capture_screen.sh"
sys.path.insert(0, str(SKILL_ROOT / "scripts"))
import normalize_png  # noqa: E402


def write_rgba(path, width, height, pixel):
    """Writes a uniform RGBA PNG whose rows use the Sub filter, as fbgrab output can."""
    rows = b""
    for _ in range(height):
        raw = bytes(pixel) * width
        rows += b"\1" + bytes((raw[i] - (raw[i - 4] if i >= 4 else 0)) & 255 for i in range(len(raw)))
    path.write_bytes(normalize_png.SIGNATURE
                     + normalize_png.chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                     + normalize_png.chunk(b"IDAT", zlib.compress(rows))
                     + normalize_png.chunk(b"IEND", b""))


def read_rgb(path):
    """Returns (color type, first pixel) of a written capture."""
    parts = list(normalize_png.chunks(path.read_bytes()))
    width, height, _, color = struct.unpack(">IIBB", parts[0][1][:10])
    channels = 4 if color == 6 else 3
    rows = normalize_png.unfilter(zlib.decompress(b"".join(body for kind, body in parts if kind == b"IDAT")),
                                  width, height, channels)
    return color, tuple(rows[0][:3])


class CaptureScreenTest(unittest.TestCase):
    def test_auto_uses_spruce_kms_with_bgra_fallback(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            bin_dir = temp / "bin"
            bin_dir.mkdir()

            ssh = bin_dir / "ssh"
            ssh.write_text(
                """#!/bin/sh
shift
command=$1
printf '%s\n' "$command" >> "$SSH_LOG"
case "$command" in
  *"command -v grim"*) exit 1 ;;
  *"echo spruce-kms"*) printf 'spruce-kms\\n' ;;
  *"[ -x /mnt/SDCARD/spruce/flip/screenshot.sh ]"*) exit 0 ;;
  *"/mnt/SDCARD/spruce/flip/screenshot.sh"*) exit 1 ;;
  *"/mnt/SDCARD/spruce/flip/arm64-ffmpeg/bin/ffmpeg"*) exit 0 ;;
  *"rm -f"*) exit 0 ;;
  *) printf 'unexpected ssh command: %s\\n' "$command" >&2; exit 1 ;;
esac
""",
                encoding="utf-8",
            )
            ssh.chmod(0o755)

            scp = bin_dir / "scp"
            scp.write_text(
                """#!/bin/sh
for argument in "$@"; do
  destination=$argument
done
cp "$CAPTURE_FIXTURE" "$destination"
""",
                encoding="utf-8",
            )
            scp.chmod(0o755)

            output = temp / "capture.png"
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            env["SSH_LOG"] = str(temp / "ssh.log")
            env["CAPTURE_FIXTURE"] = str(temp / "source.png")
            write_rgba(Path(env["CAPTURE_FIXTURE"]), 2, 2, (24, 96, 144, 0))
            result = subprocess.run(
                [str(CAPTURE_SCREEN), "spruce-test", str(output)],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(read_rgb(output), (2, (24, 96, 144)))
            self.assertIn("captured method=spruce-kms", result.stdout)
            self.assertIn("hwdownload,format=bgra", Path(env["SSH_LOG"]).read_text())

    def test_forced_fbgrab_accepts_spruce_bundled_binary(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            bin_dir = temp / "bin"
            bin_dir.mkdir()

            ssh = bin_dir / "ssh"
            ssh.write_text(
                """#!/bin/sh
shift
command=$1
printf '%s\n' "$command" >> "$SSH_LOG"
case "$command" in
  *"spruce/bin64/fbgrab"*) exit 0 ;;
  *"rm -f"*) exit 0 ;;
  *) printf 'unexpected ssh command: %s\n' "$command" >&2; exit 1 ;;
esac
""",
                encoding="utf-8",
            )
            ssh.chmod(0o755)

            scp = bin_dir / "scp"
            scp.write_text(
                """#!/bin/sh
for argument in "$@"; do
  destination=$argument
done
cp "$CAPTURE_FIXTURE" "$destination"
""",
                encoding="utf-8",
            )
            scp.chmod(0o755)

            output = temp / "capture.png"
            env = os.environ.copy()
            env["PATH"] = f"{bin_dir}:{env['PATH']}"
            env["SSH_LOG"] = str(temp / "ssh.log")
            env["CAPTURE_FIXTURE"] = str(temp / "source.png")
            write_rgba(Path(env["CAPTURE_FIXTURE"]), 2, 2, (24, 96, 144, 64))
            result = subprocess.run(
                [str(CAPTURE_SCREEN), "spruce-test", str(output), "fbgrab"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(read_rgb(output), (2, (24, 96, 144)))
            self.assertIn("captured method=fbgrab", result.stdout)
            self.assertIn("capture=/mnt/SDCARD/spruce/bin64/fbgrab", Path(env["SSH_LOG"]).read_text())


if __name__ == "__main__":
    unittest.main()
