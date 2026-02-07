# Garmin MCP

An **MCP (Model Context Protocol) server** that exposes Garmin Connect data as tools using [fastMCP](https://github.com/jlowin/fastmcp) and [garth](https://github.com/matin/garth). It talks to the official Garmin Connect API (same as the mobile app) to pull metrics, activities, and wellness data.

**Author / MCP owner:** [Lokranjan](https://github.com/lokranjanp) · [Repository](https://github.com/lokranjanp/garminmcp)

## Setup

1. **Install dependencies** (from project root):

   ```bash
   pip install -r requirements.txt
   # or: pip install -e ".[dev]"
   ```

2. **Authentication** (choose one):

   - **Recommended:** In your MCP `config.json`, pass **GARMIN_EMAIL** and **GARMIN_PASSWORD** in the server `env`. The server will log in automatically and save the session to `GARTH_SESSION_PATH` or `~/.garth` for next time.
   - Or use a saved session: set **GARTH_SESSION_PATH** (or leave default `~/.garth`) and call `garmin_resume_session()` or log in once via the `garmin_login` tool / CLI and then resume.

## Running the server

- **As a module:**

  ```bash
  python -m garmin_mcp.server
  ```

- **After installing the package:**

  ```bash
  garmin-mcp
  ```

- **With env-based auth (e.g. from MCP config):**

  ```bash
  GARMIN_EMAIL=you@example.com GARMIN_PASSWORD=secret python -m garmin_mcp.server
  ```

- **With a custom session path:**

  ```bash
  GARTH_SESSION_PATH=/path/to/session python -m garmin_mcp.server
  ```

## Tools

| Tool | Description |
|------|-------------|
| **Date/time** | |
| `garmin_current_datetime` | Current date/time (local & UTC, ISO strings, weekday, timezone) |
| **Auth & session** | |
| `garmin_login` | Log in with email/password and save session to disk |
| `garmin_resume_session` | Load a saved session from path (default `~/.garth`) |
| **User** | |
| `garmin_user_profile` | Get profile (display name, timezone, activities, etc.) |
| `garmin_user_settings` | Get settings (units, preferences) |
| **Stats (summaries)** | |
| `garmin_daily_steps` | Daily steps, distance, step goal |
| `garmin_weekly_steps` | Weekly steps summary |
| `garmin_daily_sleep_stats` | Daily sleep score/values |
| `garmin_daily_stress` | Daily stress level and durations |
| `garmin_weekly_stress` | Weekly stress |
| `garmin_daily_hydration` | Daily hydration (ml, goal) |
| `garmin_daily_intensity_minutes` | Daily intensity minutes (moderate/vigorous) |
| `garmin_weekly_intensity_minutes` | Weekly intensity minutes |
| `garmin_daily_hrv` | Daily HRV summary |
| **Data (detailed)** | |
| `garmin_sleep_data` | Full sleep data for one day |
| `garmin_sleep_data_list` | Full sleep data for a date range |
| `garmin_hrv_data` | Full HRV data for one day |
| `garmin_hrv_data_list` | Full HRV data for a date range |
| `garmin_weight` | Weight (and body composition) for one day |
| `garmin_weight_list` | Weight entries over a range |
| `garmin_body_battery_events` | Body Battery events for a day |
| `garmin_daily_body_battery_stress` | Full Body Battery + stress for a day |
| **Activities** | |
| `garmin_activities` | List activities (start, limit) |
| **Raw API** | |
| `garmin_connect_api` | Call any Connect API path (GET/POST) |

Date parameters use `YYYY-MM-DD`; optional end dates default to “today” where applicable.

## Cursor configuration

Add the server to your MCP config (e.g. Cursor MCP settings or `~/.cursor/mcp.json`). Credentials can be provided via the `env` block so the server logs in automatically:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "python",
      "args": ["-m", "garmin_mcp.server"],
      "env": {
        "GARMIN_EMAIL": "your-garmin-connect-email@example.com",
        "GARMIN_PASSWORD": "your-garmin-password"
      }
    }
  }
}
```

Optional env vars:

- **GARMIN_EMAIL** / **GARMIN_PASSWORD** — used to log in if no session exists; session is then saved for next time.
- **GARTH_SESSION_PATH** — directory to save/load session (default: `~/.garth`). If set and the folder exists, the server resumes that session before trying email/password.

## License

Use of Garth-library and this MCP is for personal use; comply with Garmin’s terms of service.
