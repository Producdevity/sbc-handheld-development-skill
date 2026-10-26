import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "resolve_portmaster_autoinstall.sh"


class PortMasterAutoinstallTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = os.environ.copy()
        self.env["HOME"] = str(self.root / "home")
        self.env.pop("XDG_DATA_HOME", None)
        self.script = self.root / "resolve.sh"
        source = SCRIPT.read_text()
        # Map device mount points into a disposable filesystem; run the real shell logic.
        source = re.sub(
            r"/(?:opt|userdata|mnt|roms2?|storage)/",
            lambda match: f"{self.root}{match[0]}", source,
        )
        self.script.write_text(source)

    def install(self, location, queue=True):
        base = self.root / location.lstrip("/")
        base.mkdir(parents=True)
        (base / "control.txt").write_text('echo "control.txt must not execute" >&2; exit 99\n')
        if queue:
            (base / "autoinstall").mkdir()
        return base

    def resolve(self, *args):
        return subprocess.run(
            ["sh", str(self.script), *map(str, args)],
            env=self.env, text=True, capture_output=True, timeout=5,
        )

    def test_firmware_installations(self):
        for location in (
            "/opt/system/Tools/PortMaster", "/opt/tools/PortMaster",
            "/userdata/system/.local/share/PortMaster", "/mnt/mmc/MUOS/PortMaster",
            "/mnt/SDCARD/Persistent/portmaster/PortMaster", "/roms/tools/PortMaster",
            "/roms2/tools/PortMaster", "/roms/ports/PortMaster",
            "/roms2/ports/PortMaster", "/storage/roms/ports/PortMaster",
            "/home/.local/share/PortMaster",
        ):
            with self.subTest(location=location):
                base = self.install(location)
                result = self.resolve()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), str(base / "autoinstall"))
                self.assertEqual(result.stderr, "")
                (base / "autoinstall").rmdir()
                (base / "control.txt").unlink()

    def test_remote_xdg_data_home(self):
        base = self.install("custom/data/PortMaster")
        self.env["XDG_DATA_HOME"] = str(base.parent)
        result = self.resolve()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(base / "autoinstall"))

    def test_aliases_of_same_installation_are_not_ambiguous(self):
        base = self.install("/storage/roms/ports/PortMaster")
        (self.root / "roms").symlink_to(base.parent.parent, target_is_directory=True)
        result = self.resolve()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(Path(result.stdout.strip()).samefile(base / "autoinstall"))

    def test_distinct_installations_require_override(self):
        self.install("/opt/tools/PortMaster")
        second = self.install("/roms/ports/PortMaster")
        result = self.resolve()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("Multiple PortMaster installations", result.stderr)
        result = self.resolve(second / "autoinstall")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(second / "autoinstall"))

    def test_custom_queue_does_not_require_standard_installation(self):
        queue = self.root / "custom" / "autoinstall"
        queue.mkdir(parents=True)
        result = self.resolve(queue)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), str(queue))

    def test_missing_installation_or_bare_queue_fails(self):
        queue = self.root / "roms/ports/PortMaster/autoinstall"
        queue.mkdir(parents=True)
        result = self.resolve()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("installation not found", result.stderr)

    def test_missing_queue_is_not_created(self):
        base = self.install("/mnt/mmc/MUOS/PortMaster", queue=False)
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*"))
        result = self.resolve()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing or not writable", result.stderr)
        self.assertFalse((base / "autoinstall").exists())
        self.assertEqual(before, sorted(str(p.relative_to(self.root)) for p in self.root.rglob("*")))

    def test_unwritable_queue_fails(self):
        queue = self.install("/roms/ports/PortMaster") / "autoinstall"
        queue.chmod(0o555)
        self.addCleanup(queue.chmod, 0o755)
        if os.access(queue, os.W_OK):
            self.skipTest("Current user bypasses write permissions")
        result = self.resolve()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("not writable", result.stderr)

    def test_invalid_or_missing_override_fails(self):
        for value in ("relative/autoinstall", "/wrong-name", str(self.root / "missing/autoinstall")):
            with self.subTest(value=value):
                result = self.resolve(value)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")


if __name__ == "__main__":
    unittest.main()
