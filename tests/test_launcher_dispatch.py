#!/usr/bin/env python3
"""Guards the zsh launcher's dispatch table against its own documentation.

The launcher ends in `*) usage` with no passthrough, so any command advertised
in its usage text or in the README that lacks a `case` branch fails at runtime
with an exit-1 usage dump. `add-allocation` shipped that way. These tests are
pure text/subprocess checks: no venv, no browser, no Concur contact.
"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = REPO_ROOT / "ccworks"
README = REPO_ROOT / "README.md"
CLI = REPO_ROOT / "src" / "ccworks" / "cli.py"

# The launcher is a dev-checkout concern: the Docker image (and a pip install)
# ship only pyproject/src/tests/README, so there is nothing to assert there.
requires_launcher = unittest.skipUnless(
    LAUNCHER.exists(), "ccworks launcher not present (packaged/container run)"
)
# The launcher is `#!/usr/bin/env zsh`; ubuntu-latest has no zsh by default.
requires_zsh = unittest.skipUnless(shutil.which("zsh"), "zsh not installed")

# `    some-command)` at the top level of the case statement.
CASE_RE = re.compile(r"^    ([a-z][a-z0-9-]*)\)$", re.MULTILINE)
# Lines inside usage(): `echo "  some-command ...`
USAGE_RE = re.compile(r'^\s*echo "  ([a-z][a-z0-9-]*)', re.MULTILINE)


def launcher_cases():
    return set(CASE_RE.findall(LAUNCHER.read_text()))


def launcher_usage_commands():
    # usage() runs from its definition to the closing `exit 1`.
    text = LAUNCHER.read_text()
    body = text[text.index("usage() {"):text.index("if [ $# -lt 1 ]")]
    return set(USAGE_RE.findall(body))


@requires_launcher
class TestLauncherDispatch(unittest.TestCase):
    def test_every_advertised_command_has_a_case_branch(self):
        missing = launcher_usage_commands() - launcher_cases()
        self.assertEqual(
            set(), missing,
            f"launcher usage() advertises commands with no case branch (they "
            f"hit `*) usage` and exit 1): {sorted(missing)}",
        )

    def test_every_readme_launcher_invocation_has_a_case_branch(self):
        invoked = set(re.findall(r"\./ccworks ([a-z][a-z0-9-]*)", README.read_text()))
        missing = invoked - launcher_cases()
        self.assertEqual(
            set(), missing,
            f"README documents `./ccworks <cmd>` for commands the launcher does "
            f"not dispatch: {sorted(missing)}",
        )

    def test_add_allocation_is_dispatched(self):
        self.assertIn("add-allocation", launcher_cases())

    @requires_zsh
    def test_add_allocation_rejects_missing_index(self):
        # The arg guard runs before ensure_venv, so this touches nothing.
        proc = subprocess.run(
            [str(LAUNCHER), "add-allocation", "Some Report"],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )
        self.assertEqual(1, proc.returncode)
        self.assertIn("transaction index", proc.stderr)


@requires_launcher
class TestLauncherVsPythonCLI(unittest.TestCase):
    """Documents the intentional divergence so it stays intentional."""

    # Renamed or wrapper-only in the launcher; reaching them by their Python
    # CLI name via `./ccworks` is expected to fail.
    KNOWN_CLI_ONLY = {"api-test", "create-report", "delete-report", "list-old-reports"}

    def test_cli_only_set_is_unchanged(self):
        cli_commands = set(re.findall(r'add_parser\("([a-z0-9-]+)"', CLI.read_text()))
        actual = cli_commands - launcher_cases()
        self.assertEqual(
            self.KNOWN_CLI_ONLY, actual,
            "the launcher/CLI command divergence changed; update the README's "
            "'Installed CLI only' list and this test together",
        )


if __name__ == "__main__":
    unittest.main()
