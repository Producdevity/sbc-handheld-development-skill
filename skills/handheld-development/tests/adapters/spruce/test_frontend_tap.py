import os
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "adapters" / "spruce" / "frontend_tap.sh"


class SpruceFrontendTapTest(unittest.TestCase):
    def run_adapter(self, *arguments: str) -> tuple[subprocess.CompletedProcess[str], str, str]:
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            fake_ssh = temporary / "ssh"
            arguments_path = temporary / "arguments"
            stdin_path = temporary / "stdin"
            fake_ssh.write_text(
                "#!/bin/sh\nprintf '%s\\n' \"$*\" >\"$SSH_ARGUMENTS\"\ncat >\"$SSH_STDIN\"\n",
                encoding="utf-8",
            )
            fake_ssh.chmod(0o755)
            environment = os.environ.copy()
            environment["PATH"] = f"{temporary}:{environment['PATH']}"
            environment["SSH_ARGUMENTS"] = str(arguments_path)
            environment["SSH_STDIN"] = str(stdin_path)
            result = subprocess.run(
                ["sh", str(SCRIPT), "spruce-test", *arguments],
                capture_output=True,
                check=False,
                env=environment,
                text=True,
                timeout=10,
            )
            ssh_arguments = arguments_path.read_text(encoding="utf-8") if arguments_path.exists() else ""
            payload = stdin_path.read_text(encoding="utf-8") if stdin_path.exists() else ""
            return result, ssh_arguments, payload

    def test_tap_is_rejected_without_calling_ssh(self) -> None:
        result, ssh_arguments, payload = self.run_adapter("tap", "face.east", "120")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(ssh_arguments, "")
        self.assertEqual(payload, "")
        self.assertIn("HOST release-all", result.stderr)

    def test_release_all_neutralizes_declared_controls(self) -> None:
        result, _ssh_arguments, payload = self.run_adapter("release-all")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 304 0\n", payload)
        self.assertIn("1 318 0\n", payload)
        self.assertIn("3 0 0\n", payload)
        self.assertIn("3 17 0\n", payload)
        self.assertTrue(payload.endswith("0 0 0\n"))

if __name__ == "__main__":
    unittest.main()
