# Garmin MCP

An **MCP (Model Context Protocol) server** that exposes Garmin Connect data as tools using [fastMCP](https://github.com/jlowin/fastmcp) and [garth](https://github.com/matin/garth). It talks to the official Garmin Connect API (same as the mobile app) to pull metrics, activities, and wellness data.

## Setup

1. **Install dependencies** (from project root):

   ```bash
   pip install -r requirements.txt
   # or: pip install -e ".[dev]"
   ```

2. **Authenticate once** (interactive or via tools):

   - Run the server and use the `garmin_login` tool with your Garmin Connect email and password, **or**
   - Log in from the command line and save the session:

     ```bash
     python -c "
     import garth
     garth.login('YOUR_EMAIL', 'YOUR_PASSWORD')
     garth.save('~/.garth')
     "
     ```

3. **Use the MCP** in Cursor or any MCP client:

   - Either call `garmin_resume_session()` (or set `GARTH_SESSION_PATH`) so the server loads the saved session.
   - Then call any of the Garmin tools (steps, sleep, stress, activities, etc.).

## Running the server

- **As a module:**

  ```bash
  python -m garmin_mcp.server
  ```

- **After installing the package:**

  ```bash
  garmin-mcp
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

Add the server to your MCP config (e.g. Cursor MCP settings or `~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "garmin": {
      "command": "python",
      "args": ["-m", "garmin_mcp.server"],
      "env": {
        "GARTH_SESSION_PATH": "/path/to/your/.garth"
      }
    }
  }
}
```

If you don’t set `GARTH_SESSION_PATH`, the server will try `~/.garth` when a tool needs the API.

## License

Use of Garth-library and this MCP is for personal use; comply with Garmin’s terms of service.
