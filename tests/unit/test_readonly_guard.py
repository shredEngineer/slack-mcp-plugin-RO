"""Tests for the read-only guard hook (hooks/slack-readonly-guard.py).

The guard is a PreToolUse hook: it reads a tool call as JSON on stdin and either
stays silent (the call is allowed to proceed through normal permission flow) or
emits a PreToolUse `permissionDecision: "deny"` to block the call. This fork is
read-only, so every Slack write/mutating tool — and any unrecognized Slack tool —
must be denied, while Slack read tools and all non-Slack tools pass through.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

GUARD = Path(__file__).resolve().parents[2] / "hooks" / "slack-readonly-guard.py"


def run_guard(tool_name: str) -> tuple[int, str]:
    """Invoke the guard with a tool call; return (exit_code, stdout)."""
    payload = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool_name, "tool_input": {}})
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=payload,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout


def is_deny(exit_code: int, stdout: str) -> bool:
    """A deny is exit 0 with a PreToolUse permissionDecision of 'deny'."""
    if exit_code != 0 or not stdout.strip():
        return False
    decision = json.loads(stdout).get("hookSpecificOutput", {})
    return decision.get("permissionDecision") == "deny"


def is_pass(exit_code: int, stdout: str) -> bool:
    """A pass-through is exit 0 with no decision emitted."""
    return exit_code == 0 and not stdout.strip()


WRITE_TOOLS = [
    "mcp__slack__slack_send_message",
    "mcp__slack__slack_send_message_draft",
    "mcp__slack__slack_add_reaction",
    "mcp__slack__slack_schedule_message",
    "mcp__slack__slack_create_canvas",
]

READ_TOOLS = [
    "mcp__slack__slack_read_channel",
    "mcp__slack__slack_read_thread",
    "mcp__slack__slack_read_user_profile",
    "mcp__slack__slack_search_public",
    "mcp__slack__slack_search_public_and_private",
    "mcp__slack__slack_search_channels",
    "mcp__slack__slack_search_users",
    "mcp__slack__slack_list_channel_members",
]


@pytest.mark.parametrize("tool", WRITE_TOOLS)
def test_write_tools_are_denied(tool: str):
    assert is_deny(*run_guard(tool)), f"{tool} must be denied"


@pytest.mark.parametrize("tool", READ_TOOLS)
def test_read_tools_pass_through(tool: str):
    assert is_pass(*run_guard(tool)), f"{tool} must pass through"


def test_unknown_slack_tool_is_denied():
    # Default-deny: a Slack tool we don't recognize is treated as a potential write.
    assert is_deny(*run_guard("mcp__slack__slack_set_status")), "unknown Slack tool must default-deny"


def test_namespaced_slack_write_is_denied():
    # Namespace-agnostic: blocks regardless of how the server is namespaced.
    assert is_deny(*run_guard("mcp__slack-plugin__slack__slack_send_message"))


@pytest.mark.parametrize(
    "tool",
    ["Read", "Bash", "Edit", "mcp__github__create_issue", "mcp__other__do_thing"],
)
def test_non_slack_tools_pass_through(tool: str):
    assert is_pass(*run_guard(tool)), f"{tool} must pass through"
