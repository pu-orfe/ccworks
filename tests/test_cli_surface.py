#!/usr/bin/env python3
"""Invariants for the single-front-door command surface.

The parser is a front-end that normalizes `<group> <subcommand>` onto the
dispatcher's internal command tokens. The dangerous failure mode is drift: a
group/subcommand that maps to no dispatcher branch (runtime crash), or a
dispatcher branch no longer reachable from any command (dead code). The closure
test below pins both directions.
"""
import argparse
import pathlib
import re
import subprocess
import sys
import unittest
from argparse import Namespace

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from ccworks.cli import (  # noqa: E402
    LEGACY_COMMANDS,
    _legacy_command,
    build_parser,
)

CLI_SOURCE = (REPO_ROOT / "src" / "ccworks" / "cli.py").read_text()

# Subcommands whose token depends on a flag, and the flags that switch them.
FLAG_DEPENDENT = {
    ("report", "list"): ("historical", ["query", "list-old-reports"]),
    ("report", "delete"): ("all_drafts", ["delete-report", "delete-all-reports"]),
}


def parser_surface():
    """-> {(group, subcommand_or_None)} for every command the parser accepts."""
    parser, _ = build_parser()
    top = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    surface = set()
    for group_name, group_parser in top.choices.items():
        nested = [a for a in group_parser._actions if isinstance(a, argparse._SubParsersAction)]
        if not nested:
            surface.add((group_name, None))
            continue
        for sub_name in nested[0].choices:
            surface.add((group_name, sub_name))
    return surface


def dispatcher_tokens():
    """-> {token} for every `args.command == "token"` branch in the dispatcher."""
    return set(re.findall(r'args\.command == "([a-z0-9-]+)"', CLI_SOURCE))


def producible_tokens():
    """-> {token} reachable from the parser surface, both flag variants included."""
    tokens = set()
    for group, sub in parser_surface():
        if (group, sub) in FLAG_DEPENDENT:
            attr, expected = FLAG_DEPENDENT[(group, sub)]
            for value in (False, True):
                ns = Namespace(group=group, subcommand=sub, **{attr: value})
                tokens.add(_legacy_command(ns))
            continue
        ns = Namespace(group=group, subcommand=sub)
        token = _legacy_command(ns)
        if token is not None:
            tokens.add(token)
    return tokens


class TestSurfaceClosure(unittest.TestCase):
    def test_every_command_maps_to_a_dispatcher_branch(self):
        unmapped = [
            (g, s) for g, s in parser_surface()
            if _legacy_command(Namespace(group=g, subcommand=s, historical=False, all_drafts=False)) is None
        ]
        self.assertEqual(
            [], unmapped,
            f"parser accepts commands that map to no dispatcher token: {unmapped}",
        )

    def test_no_orphaned_dispatcher_branches(self):
        orphans = dispatcher_tokens() - producible_tokens()
        self.assertEqual(
            set(), orphans,
            f"dispatcher handles tokens no command can produce (dead code): {sorted(orphans)}",
        )

    def test_no_unhandled_tokens(self):
        unhandled = producible_tokens() - dispatcher_tokens()
        self.assertEqual(
            set(), unhandled,
            f"commands produce tokens the dispatcher does not handle: {sorted(unhandled)}",
        )

    def test_flag_dependent_commands_resolve_both_ways(self):
        for (group, sub), (attr, expected) in FLAG_DEPENDENT.items():
            got = [
                _legacy_command(Namespace(group=group, subcommand=sub, **{attr: value}))
                for value in (False, True)
            ]
            self.assertEqual(expected, got, f"{group} {sub} --{attr}")


class TestRetiredNames(unittest.TestCase):
    def test_no_retired_name_collides_with_a_group(self):
        groups = {g for g, _ in parser_surface()}
        collisions = groups & set(LEGACY_COMMANDS)
        self.assertEqual(
            set(), collisions,
            f"retired names shadow live groups, so they'd be intercepted: {sorted(collisions)}",
        )

    def test_every_suggestion_is_a_real_command(self):
        surface = parser_surface()
        groups = {g for g, _ in surface}
        for old, suggestion in LEGACY_COMMANDS.items():
            parts = suggestion.split()
            self.assertIn(parts[0], groups, f"{old} -> unknown group '{parts[0]}'")
            if (parts[0], None) in surface:  # top-level command such as nuke
                continue
            self.assertIn(
                (parts[0], parts[1]), surface,
                f"{old} -> '{parts[0]} {parts[1]}' is not a real command",
            )

    def test_retired_names_exit_2_with_a_suggestion(self):
        for old in sorted(LEGACY_COMMANDS):
            proc = subprocess.run(
                [sys.executable, "-m", "ccworks.cli", old],
                capture_output=True, text=True, cwd=REPO_ROOT,
                env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT / "src")},
            )
            self.assertEqual(2, proc.returncode, f"{old}: expected exit 2, got {proc.returncode}")
            self.assertIn("unrecognized command", proc.stderr, old)
            self.assertIn("Did you mean", proc.stderr, old)
            self.assertIn(LEGACY_COMMANDS[old], proc.stderr, old)


class TestGuards(unittest.TestCase):
    """Flag combinations that must be refused rather than silently misfire."""

    def _run(self, *argv):
        return subprocess.run(
            [sys.executable, "-m", "ccworks.cli", *argv],
            capture_output=True, text=True, cwd=REPO_ROOT,
            env={**__import__("os").environ, "PYTHONPATH": str(REPO_ROOT / "src")},
        )

    def test_receipt_delete_requires_all(self):
        proc = self._run("receipt", "delete")
        self.assertEqual(2, proc.returncode)
        self.assertIn("requires --all", proc.stderr)

    def test_report_delete_needs_a_target(self):
        proc = self._run("report", "delete")
        self.assertEqual(2, proc.returncode)
        self.assertIn("needs a report NAME", proc.stderr)

    def test_report_delete_rejects_both_targets(self):
        proc = self._run("report", "delete", "R", "--all-drafts")
        self.assertEqual(2, proc.returncode)
        self.assertIn("not both", proc.stderr)

    def test_view_without_historical_is_refused(self):
        # Silently ignoring --view here would misreport which reports were listed.
        proc = self._run("report", "list", "--view", "All Reports")
        self.assertEqual(2, proc.returncode)
        self.assertIn("--historical", proc.stderr)

    def test_bare_invocation_prints_reference_and_exits_zero(self):
        proc = self._run()
        self.assertEqual(0, proc.returncode)
        self.assertIn("report list", proc.stderr)

    def test_group_without_subcommand_shows_group_help(self):
        proc = self._run("report")
        self.assertEqual(2, proc.returncode)
        self.assertIn("reconcile", proc.stderr)


if __name__ == "__main__":
    unittest.main()
