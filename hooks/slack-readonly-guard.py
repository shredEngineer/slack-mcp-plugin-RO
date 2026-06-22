#!/usr/bin/env python3
"""PreToolUse guard that makes this a read-only Slack plugin.

This fork must be able to read from Slack but must NEVER write/post/mutate. The
write tools are defined by Slack's hosted MCP server, not by this repo, so they
cannot be deleted here — they have to be blocked at the harness layer before the
call leaves the client. Claude Code invokes this script before a matching tool
runs, passing the tool call as JSON on stdin.

Policy (fail-closed, default-deny):
  * Only Slack MCP tools are governed. A tool is "Slack" when its bare name (the
    segment after the last "__") starts with "slack_". This is namespace-agnostic
    and works whether the tool arrives as `mcp__slack__slack_send_message` or
    under any extra plugin namespacing.
  * A Slack tool is allowed ONLY if its bare name is in READ_ALLOWLIST. Anything
    else — every known write tool AND any unrecognized Slack tool — is denied.
  * Non-Slack tools (file reads, Bash, other MCP servers) pass through untouched.

A denied call emits a PreToolUse `permissionDecision: "deny"`; an allowed call
emits nothing and lets the normal permission flow continue.
"""

import json
import sys

# Slack read tools that are safe in a read-only fork. To allow a newly added
# read tool, add its bare name here — a deliberate, reviewable change. Everything
# not on this list is denied by default, so new write tools are blocked for free.
READ_ALLOWLIST = frozenset(
    {
        "slack_read_channel",
        "slack_read_thread",
        "slack_read_user_profile",
        "slack_search_public",
        "slack_search_public_and_private",
        "slack_search_channels",
        "slack_search_users",
        "slack_list_channel_members",
    }
)

# All Slack MCP tool names follow this convention.
SLACK_TOOL_PREFIX = "slack_"


def decide(tool_name: str) -> str | None:
    """Return a denial reason for a blocked Slack tool, or None to allow."""
    bare = tool_name.rsplit("__", 1)[-1]
    if not bare.startswith(SLACK_TOOL_PREFIX):
        return None  # not a Slack tool — none of our business
    if bare in READ_ALLOWLIST:
        return None  # a known read tool — allowed
    return (
        f"Blocked Slack tool '{bare}': this is a read-only Slack plugin and never "
        f"writes, posts, or mutates Slack. Only read/search tools are permitted."
    )


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        # Malformed input: fail closed for safety, but don't crash the harness.
        payload = {}

    tool_name = payload.get("tool_name", "")
    reason = decide(tool_name)
    if reason is None:
        return 0  # allow: stay silent, let normal permission flow continue

    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        },
        sys.stdout,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
