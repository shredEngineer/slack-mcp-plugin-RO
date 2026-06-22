# Read-Only Enforcement — Design Spec

**Date:** 2026-06-22
**Status:** Approved
**Scope:** This fork is a read-only (RO) variant of the Slack plugin. It must be able to
*read* from Slack and must **never** write/post/mutate anything.

## Problem

All Slack capabilities reach the client at runtime over MCP from Slack's hosted server
(`https://mcp.slack.com/mcp`). The write tools (`slack_send_message`,
`slack_send_message_draft`, `slack_add_reaction`, `slack_schedule_message`,
`slack_create_canvas`, …) are **defined by that server**, not by this repo — so there is
nothing here to "delete". A flag in a doc/CLAUDE.md is only a soft prompt hint the model
could ignore. A hard guarantee requires the **harness** to block the calls before they
leave the client.

We control the harness, not the server, and we keep the integration declarative (no
self-hosted proxy). Therefore: enforce read-only at the harness layer, fail-closed.

## Approach: harness-level deny, defense in depth

Three layers, hardcoded (no toggle — this is a permanent RO fork).

### Layer 1 — PreToolUse guard hook (primary, future-proof)

`hooks/slack-readonly-guard.py` — a Python 3 script invoked before every matching tool
call. It receives the tool call as JSON on stdin and decides:

- It only acts on Slack MCP tools. A tool is "Slack" when the bare tool name (the segment
  after the last `__`) starts with `slack_`. This is namespace-agnostic: it works whether
  the tool arrives as `mcp__slack__slack_send_message` or under any plugin namespacing.
- **Default-deny against a read allowlist.** The bare tool name must be in the read
  allowlist, otherwise the call is denied. Read allowlist:
  - `slack_read_channel`
  - `slack_read_thread`
  - `slack_read_user_profile`
  - `slack_search_public`
  - `slack_search_public_and_private`
  - `slack_search_channels`
  - `slack_search_users`
  - `slack_list_channel_members`
- Non-Slack tools (file reads, Bash, other MCP servers) pass through untouched.
- A denied call returns a PreToolUse `permissionDecision: "deny"` JSON with a clear reason;
  the model sees why and cannot proceed.

**Consequence:** any *new or unknown* Slack write tool (e.g. a future canvas/upload tool)
is blocked automatically, because it is not on the allowlist. A new *read* tool that gets
blocked is a deliberate one-line allowlist addition — never a silent leak.

Wired in two places so it applies both when the plugin is installed and when developing in
this repo:
- `hooks/hooks.json` (plugin hook, script path via `${CLAUDE_PLUGIN_ROOT}`), referenced
  from `.claude-plugin/plugin.json` via `"hooks": "./hooks/hooks.json"`.
- `.claude/settings.json` → `hooks.PreToolUse` (script path via `$CLAUDE_PROJECT_DIR`).

Hook matcher: `mcp__.*slack.*` (broad; the guard re-checks precisely).

### Layer 2 — `permissions.deny` (static belt)

`.claude/settings.json` → `permissions.deny` lists the known write tools explicitly:
`mcp__slack__slack_send_message`, `…_send_message_draft`, `…_add_reaction`,
`…_schedule_message`, `…_create_canvas`. Redundant with the hook, but visible in the diff
and enforced even if a hook is disabled.

### Layer 3 — remove write paths from commands / skills / docs

Nothing in the plugin should *suggest* writing:
- `commands/draft-announcement.md` — neutralized: still composes the announcement text,
  but the `slack_send_message_draft` step is removed; the text is presented for the user to
  paste manually.
- `commands/standup.md` — step 6 no longer offers to "post it"; the user copies it into
  Slack themselves.
- `skills/slack-messaging/SKILL.md` — write-tool references removed; it stays a pure
  formatting guide.
- `README.md`, `AGENTS.md`, both `plugin.json` `description` fields — reworded from
  "send communications" to read-only language.

## Testing

`tests/unit/test_readonly_guard.py` (runs in CI via `make test-unit`) drives the guard via
subprocess and asserts:
- write tool → deny
- read tool → pass
- unknown Slack tool → deny (default-deny)
- non-Slack tool → pass

## Known limitation

The hard guarantee targets **Claude Code** (the maintainer's environment). Cursor's hook
support differs and `permissions.deny` is a Claude Code construct; under Cursor the soft
(docs/commands) layer applies but the harness-hard layer may not. Documented, not solved.
