# Garmin MCP

MCP server that exposes Garmin Connect data (steps, sleep, stress, activities, etc.) via [garth](https://github.com/matin/garth) and [fastMCP](https://github.com/jlowin/fastmcp). Auth: set `GARMIN_EMAIL` and `GARMIN_PASSWORD` in env, or use a saved session at `~/.garth` (or `GARTH_SESSION_PATH`).

## MCP config

Use **full path** to `uvx` (e.g. `which uvx`). Example for Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`) or Cursor:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "/Users/YOUR_USER/.local/bin/uvx",
      "args": ["--from", "git+https://github.com/lokranjanp/garminmcp", "garmin-mcp"],
      "env": {
        "GARMIN_EMAIL": "your-garmin-email@example.com",
        "GARMIN_PASSWORD": "your-password"
      }
    }
  }
}
```

From PyPI (if published): `"args": ["garmin-mcp"]`.

## Commands

```bash
uv sync                    # install from uv.lock
uv run garmin-mcp          # run server locally
uv lock                    # refresh lock after changing pyproject.toml
```

## Tools

| Tool | Description |
|------|-------------|
| **Utility** | |
| `garmin_current_datetime` | Current date/time (local & UTC, ISO, weekday) |
| **Auth** | |
| `garmin_login` | Log in and save session to disk |
| `garmin_resume_session` | Load saved session |
| **User** | |
| `garmin_user_profile` | Profile (display name, timezone, etc.) |
| `garmin_user_settings` | Settings (units, preferences) |
| **Stats** | |
| `garmin_daily_steps` | Daily steps, distance, goal |
| `garmin_weekly_steps` | Weekly steps |
| `garmin_daily_sleep_stats` | Daily sleep score |
| `garmin_daily_stress` / `garmin_weekly_stress` | Stress |
| `garmin_daily_hydration` | Hydration (ml, goal) |
| `garmin_daily_intensity_minutes` / `garmin_weekly_intensity_minutes` | Intensity minutes |
| `garmin_daily_hrv` | Daily HRV summary |
| **Data** | |
| `garmin_sleep_data` / `garmin_sleep_data_list` | Sleep (single day or range) |
| `garmin_hrv_data` / `garmin_hrv_data_list` | HRV (single day or range) |
| `garmin_weight` / `garmin_weight_list` | Weight / body composition |
| `garmin_body_battery_events` | Body Battery events |
| `garmin_daily_body_battery_stress` | Body Battery + stress for a day |
| **Activities** | |
| `garmin_activities` | List activities (start, limit) |
| `garmin_activity_details` | Full details for one activity by ID (running, strength, etc.) |
| `garmin_activity_types` | List all activity types (type IDs and keys) |
| **Biomarkers & summary** | |
| `garmin_daily_summary` | One-day wellness: RHR, HR, stress, steps, SpO2, respiration, body battery, calories |
| `garmin_resting_heart_rate` | Resting heart rate for a date range |
| **Raw API** | |
| `garmin_connect_api` | Call any Connect API path (GET/POST) |

Dates: use `YYYY-MM-DD`; omit end date for “today” where supported.
