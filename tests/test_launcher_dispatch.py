#!/usr/bin/env python3
"""Guards the zsh launcher's role as a thin passthrough.

There is one command surface (the Python CLI). The launcher may own only the
checkout-only chores — setup and the test targets — and must forward everything
else verbatim. A launcher that grows its own product commands, or renames one,
recreates the two-front-doors problem these tests exist to prevent.

Pure text/subprocess checks: no venv, no browser, no Concur contact.
"""
import re
import shutil
import subprocess
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
LAUNCHER = REPO_ROOT / "ccworks"
README = REPO_ROOT / "README.md"

# The only commands the launcher is allowed to handle itself.
DEV_TASKS = {
    "setup",
    "test-local",
    "test-docker",
    "test-browser-smoke",
    "test-reports-live",
    "test-receipts-live",
}

CASE_RE = re.compile(r"^    ([a-z*][a-z0-9-]*)\)$", re.MULTILINE)
USAGE_RE = re.compile(r'^\s*echo "  ([a-z][a-z0-9-]*)', re.MULTILINE)

# The launcher is a dev-checkout concern: the Docker image ships only
# pyproject/src/tests/README, so there is nothing to assert there.
requires_launcher = unittest.skipUnless(
    LAUNCHER.exists(), "ccworks launcher not present (packaged/container run)"
)
requires_zsh = unittest.skipUnless(shutil.which("zsh"), "zsh not installed")


def launcher_cases():
    return set(CASE_RE.findall(LAUNCHER.read_text()))


@requires_launcher
class TestLauncherIsThinPassthrough(unittest.TestCase):
    def test_launcher_handles_only_dev_tasks_and_a_catchall(self):
        self.assertEqual(
            DEV_TASKS | {"*"}, launcher_cases(),
            "the launcher must handle only dev chores plus a `*` forwarding case; "
            "product commands belong to the CLI",
        )

    def test_catchall_forwards_all_arguments(self):
        text = LAUNCHER.read_text()
        catchall = text[text.index("    *)"):]
        self.assertIn(
            'run_cli "$@"', catchall,
            "the catch-all must forward the full argument list verbatim",
        )

    def test_usage_advertises_exactly_the_dev_tasks(self):
        text = LAUNCHER.read_text()
        body = text[text.index("usage() {"):text.index("# Activate the local dev venv")]
        self.assertEqual(
            DEV_TASKS, set(USAGE_RE.findall(body)),
            "launcher usage() must list exactly the dev tasks it dispatches",
        )


@requires_launcher
@requires_zsh
class TestLauncherBehaviour(unittest.TestCase):
    def _run(self, *argv):
        return subprocess.run(
            [str(LAUNCHER), *argv], capture_output=True, text=True, cwd=REPO_ROOT
        )

    def test_forwarded_help_matches_the_cli_exactly(self):
        via_launcher = self._run("report", "list", "--help")
        direct = subprocess.run(
            ["python", "-m", "ccworks.cli", "report", "list", "--help"],
            capture_output=True, text=True, cwd=REPO_ROOT,
            env={**__import__("os").environ,
                 "PATH": f"{REPO_ROOT / '.venv' / 'bin'}:{__import__('os').environ['PATH']}"},
        )
        self.assertEqual(direct.stdout, via_launcher.stdout)

    def test_retired_name_surfaces_the_cli_error(self):
        # The launcher must not intercept retired names itself; the CLI owns
        # the "did you mean" guidance so both front doors say the same thing.
        proc = self._run("query-old")
        self.assertIn("unrecognized command", proc.stderr)
        self.assertIn("report list --historical", proc.stderr)


@requires_launcher
class TestDocsUseTheLiveSurface(unittest.TestCase):
    def test_readme_has_no_retired_launcher_invocations(self):
        import sys
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from ccworks.cli import LEGACY_COMMANDS

        invoked = set(re.findall(r"\./ccworks ([a-z][a-z0-9-]*)", README.read_text()))
        retired = invoked & set(LEGACY_COMMANDS)
        self.assertEqual(
            set(), retired,
            f"README documents retired commands: {sorted(retired)}",
        )

    def test_readme_launcher_invocations_are_dev_tasks_or_live_groups(self):
        import sys
        sys.path.insert(0, str(REPO_ROOT / "src"))
        from ccworks.cli import build_parser

        _, group_parsers = build_parser()
        allowed = DEV_TASKS | set(group_parsers) | {"nuke"}
        invoked = set(re.findall(r"\./ccworks ([a-z][a-z0-9-]*)", README.read_text()))
        unknown = invoked - allowed
        self.assertEqual(
            set(), unknown,
            f"README invokes commands that are neither dev tasks nor CLI groups: {sorted(unknown)}",
        )


if __name__ == "__main__":
    unittest.main()
