import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import discover_artifacts


class DiscoverArtifactsTest(unittest.TestCase):
    def test_cli_filters_by_age_category_and_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            recent_input = root / "sample_input.py"
            recent_input.write_text("import uinput\n", encoding="utf-8")
            old_input = root / "sample_old_input.py"
            old_input.write_text("import uinput\n", encoding="utf-8")
            old_time = time.time() - 10 * 86400
            os.utime(old_input, (old_time, old_time))
            debugger = root / "sample_debug.py"
            debugger.write_text("run gdbserver\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(discover_artifacts.__file__)),
                    str(root),
                    "--modified-within-days",
                    "2",
                    "--category",
                    "input",
                    "--path-contains",
                    "sample",
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn(str(recent_input), result.stdout)
            self.assertNotIn(str(old_input), result.stdout)
            self.assertNotIn(str(debugger), result.stdout)

    def test_specialized_formats_are_classified(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            evemu = root / "controller.evemu"
            evemu.write_text("N: test controller\n", encoding="utf-8")
            r2 = root / "trace.r2"
            r2.write_text("aaa\nafl\n", encoding="utf-8")

            self.assertIn(
                "input",
                discover_artifacts.inspect(evemu, 1024, False, "project")["categories"],
            )
            self.assertIn(
                "reverse",
                discover_artifacts.inspect(r2, 1024, False, "project")["categories"],
            )

    def test_sdl_underscore_name_is_found(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample_sdl_mapping.py"
            path.write_text("probe = 'SDL_GameControllerMappingForGUID'\n", encoding="utf-8")
            record = discover_artifacts.inspect(path, 1024, False, "temporary")
            self.assertIsNotNone(record)
            self.assertIn("input", record["categories"])

    def test_symlinks_are_not_read(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.py"
            target.write_text("uinput\n", encoding="utf-8")
            link = root / "helper.py"
            link.symlink_to(target)
            self.assertIsNone(
                discover_artifacts.inspect(link, 1024, True, "project")
            )

    def test_extensionless_file_requires_shebang(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            lock = root / "lock"
            lock.write_text("1234\n", encoding="utf-8")
            helper = root / "probe"
            helper.write_text("#!/bin/sh\nreadelf app\n", encoding="utf-8")
            self.assertIsNone(
                discover_artifacts.inspect(lock, 1024, True, "temporary")
            )
            self.assertIsNotNone(
                discover_artifacts.inspect(helper, 1024, True, "temporary")
            )

    def test_project_scan_keeps_tools_but_skips_generic_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tool = root / ".agents" / "tools" / "helper.py"
            tool.parent.mkdir(parents=True)
            tool.write_text("print('custom helper')\n", encoding="utf-8")
            source = root / "src" / "main.c"
            source.parent.mkdir()
            source.write_text("/* controller */\n", encoding="utf-8")

            candidates = {path for path, _ in discover_artifacts.iter_project_files(root)}
            self.assertIn(tool, candidates)
            self.assertNotIn(source, candidates)


if __name__ == "__main__":
    unittest.main()
