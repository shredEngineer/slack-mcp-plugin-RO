# Slack Plugin (Read-Only)

This repository contains the configuration needed to integrate Slack with Cursor IDE and Claude Code. The plugin lets your agents **read** from your Slack workspace — searching and reading messages, threads, channels, and user profiles — all through natural language.

> **🔒 Read-only fork.** This variant is hard-locked to reading. It can never send, post, draft, react, schedule, or otherwise write to Slack. Enforcement is at the harness layer (a `permissions.deny` list plus a default-deny PreToolUse guard hook), not just guidance — see [Read-only enforcement](#read-only-enforcement) below.

## Features

The Slack MCP server exposes many capabilities; this fork permits only the read-only ones:

- **Search**: Find messages, files, users, and channels (both public and private)
- **Read**: Retrieve channel histories and access threaded conversations
- **User Management**: Retrieve user profiles including custom fields and status information

Write capabilities the upstream server offers (sending messages, reactions, scheduling, canvas creation) are **blocked** in this fork.

## Prerequisites

Before setting up the Slack MCP server, ensure you have:

- Cursor IDE or Claude Code CLI installed
- Access to a Slack workspace with MCP integration approved by your workspace admin

## Installation

Choose the installation method for your IDE:

### Claude Code

If you're using Claude Code CLI, you can install this as a plugin by cloning it locally:

```bash
git clone https://github.com/slackapi/slack-mcp-plugin.git
cd slack-mcp-plugin
claude --plugin-dir ./
```

The Slack MCP server will be automatically configured when the plugin loads. You will be prompted to authenticate into your Slack workspace via OAuth.

The Claude plugin uses the following MCP configuration (`.mcp.json`):

```json
{
  "mcpServers": {
    "slack": {
      "type": "http",
      "url": "https://mcp.slack.com/mcp",
      "oauth": {
        "clientId": "1601185624273.8899143856786",
        "callbackPort": 3118
      }
    }
  }
}
```

### Cursor

You can use the following Add to Cursor button or follow the steps below to manually configure the Slack MCP server in Cursor:

[![Install MCP Server](https://cursor.com/deeplink/mcp-install-dark.svg)](https://cursor.com/en-US/install-mcp?name=slack&config=eyJ1cmwiOiJodHRwczovL21jcC5zbGFjay5jb20vbWNwIiwiYXV0aCI6eyJDTElFTlRfSUQiOiIzNjYwNzUzMTkyNjI2Ljg5MDM0NjkyMjg5ODIifX0%3D)

#### Step 1: Open Cursor Settings

Navigate to **Cursor → Settings → Cursor Settings** (or use the keyboard shortcut `Cmd+,` on macOS, `Ctrl+,` on Windows/Linux).

#### Step 2: Navigate to MCP Tab

In the Settings interface, click on the **MCP** tab to access MCP server configurations.

#### Step 3: Add Slack MCP Configuration

Add the following configuration to connect to the remote Slack MCP server:

```json
{
  "mcpServers": {
    "slack": {
      "url": "https://mcp.slack.com/mcp",
      "auth": {
        "CLIENT_ID": "3660753192626.8903469228982"
      }
    }
  }
}
```

Save the configuration. You will also see a connect button once added. Click that to authenticate into your Slack Workspace.

## Usage Examples

Once configured, you can interact with Slack through your AI assistant using natural language:

- **Search messages**: "Search for messages about the product launch in the last week"
- **Read channels**: "Summarize the last 50 messages in #engineering"
- **Find users**: "Who is the user with email john@example.com?"
- **Access threads**: "Show me the conversation thread from that message"

Write requests (e.g. "send a message to #general") are intentionally refused — the guard hook blocks them before they reach Slack.

## Read-only enforcement

The write tools (`slack_send_message`, `slack_add_reaction`, `slack_schedule_message`, canvas creation, …) are defined by Slack's hosted MCP server, not by this repo — so they can't simply be removed here. Instead this fork blocks them at the **harness layer**, fail-closed and defense-in-depth:

1. **Default-deny guard hook** — [`hooks/slack-readonly-guard.py`](hooks/slack-readonly-guard.py) runs as a `PreToolUse` hook before every Slack tool call. It allows a tool **only** if it is on an explicit read allowlist; everything else — including any *new or unknown* Slack tool — is denied. This is the primary, future-proof guarantee. It is wired via [`hooks/hooks.json`](hooks/hooks.json) (plugin install) and `.claude/settings.json` (in-repo development).
2. **`permissions.deny` list** — `.claude/settings.json` additionally names the known write tools explicitly, as a visible, static belt.
3. **No write paths in commands/skills** — the bundled commands and skills compose text for *you* to post; none of them write to Slack.

The allowlisted (permitted) tools are: `slack_read_channel`, `slack_read_thread`, `slack_read_user_profile`, `slack_search_public`, `slack_search_public_and_private`, `slack_search_channels`, `slack_search_users`, `slack_list_channel_members`.

> **Scope:** the harness-hard guarantee targets **Claude Code**. Cursor's hook support differs and `permissions.deny` is a Claude Code construct, so under Cursor only the soft (commands/skills/docs) layer applies. If you need a hard guarantee under any client, point `.mcp.json` at a read-only MCP proxy instead.

## Documentation & Resources

- [Official Slack MCP Server Documentation](https://docs.slack.dev/ai/mcp-server/)

## Notes & Limitations

- **Remote server only**: This configuration connects to Slack's hosted MCP server. No local installation is required or supported.
- **Admin approval required**: Your Slack workspace administrator must approve MCP integration before you can use this feature.

## Questions or Issues?

For questions about the Slack MCP server or integration issues, please refer to the [official Slack documentation](https://docs.slack.dev/ai/mcp-server/) or contact your workspace administrator.
