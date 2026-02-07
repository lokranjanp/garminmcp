# Clear caches and force Claude to use your repo

## 1. Clear uv cache 

```bash
uv cache clean
```

Or manually remove the cache directory (macOS):

```bash
rm -rf ~/.cache/uv
# or if uv uses XDG:
rm -rf ~/Library/Caches/uv
```

## 2. Use a NEW MCP server name (avoids Claude reusing cached "garmin")

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` and **remove** the `"garmin"` entry. Add a **new** key so Claude doesn’t reuse old config:

```json
{
  "mcpServers": {
    "garmin-connect": {
      "command": "/Users/lokranjan.p/.local/bin/uvx",
      "args": ["--python", "3.12", "--from", "git+https://github.com/lokranjanp/garminmcp", "garmin-mcp"],
      "env": {
        "GARMIN_EMAIL": "your-email",
        "GARMIN_PASSWORD": "your-password"
      }
    }
  },
  "preferences": { ... }
}
```

Save the file.

## 3. Fully quit Claude and clear its in-memory/cached config

- Quit Claude Desktop (Cmd+Q or Claude → Quit).
- Optional: force-quit so no process keeps old config:
  - Activity Monitor → search “Claude” → Quit (or Force Quit) all Claude processes.

## 4. Reopen Claude Desktop

Open Claude again. It will read the config from disk and spawn `garmin-connect` with your repo.

## 5. Check the latest log lines

Logs: `~/Library/Logs/Claude/` (look for MCP-related log files).

Confirm the **newest** log entries (after the restart) show:

`git+https://github.com/lokranjanp/garminmcp`

Old log lines from before the config change will still show the old URL.
