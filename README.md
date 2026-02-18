# Garmin MCP

MCP server that exposes Garmin Connect data (steps, sleep, stress, activities, etc.) via [garth](https://github.com/matin/garth) and [fastMCP](https://github.com/jlowin/fastmcp). Auth: set `GARMIN_EMAIL` and `GARMIN_PASSWORD` in env, or use a saved session at `~/.garth` (or `GARTH_SESSION_PATH`).

## MCP config

Use **full path** to `uvx` (e.g. `which uvx`). Example for Claude Desktop (`~/Library/Application Support/Claude/claude_desktop_config.json`) or Cursor:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "/Users/YOUR_USER/.local/bin/uvx",
      "args": ["--refresh", "--from", "git+https://github.com/lokranjanp/garminmcp", "garmin-mcp"],
      "env": {
        "GARMIN_EMAIL": "your-garmin-email@example.com",
        "GARMIN_PASSWORD": "your-password",

        "SMTP_HOST": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USER": "your-email@gmail.com",
        "SMTP_PASSWORD": "your-app-password",
        "SMTP_TO": "recipient@example.com",
        "OUTPUT_DIR": "/Users/user.mac/garmin_data/",

        "LLM_API_BASE": "http://localhost:1234/v1",
        "LLM_API_KEY": "lm-studio",
        "LLM_MODEL": "your-loaded-model-name"
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

## Tools (17 base + 3 opt-in)

| # | Tool | Description |
|---|------|-------------|
| | **Utility** | |
| 1 | `garmin_current_datetime` | Current date/time (local & UTC, ISO, weekday) |
| | **Auth** | |
| 2 | `garmin_login` | Log in and save session to disk |
| 3 | `garmin_resume_session` | Load saved session |
| | **User** | |
| 4 | `garmin_user_profile` | Profile (display name, timezone, etc.) |
| 5 | `garmin_user_settings` | Settings (units, preferences) |
| | **Metrics (daily/weekly series)** | |
| 6 | `garmin_metric` | Fetch daily or weekly stat series. `metric`: steps, sleep, stress, hydration, intensity_minutes, hrv. `period`: daily or weekly. `count`: number of periods. |
| | **Detailed health data** | |
| 7 | `garmin_data` | Fetch detailed data (single day or list). `data_type`: sleep, hrv, weight, body_battery_events, body_battery_stress. Use `day` for single-day or `end_date`+`days` for a range. |
| | **Activities** | |
| 8 | `garmin_activities` | List activities (start, limit) |
| 9 | `garmin_activity_details` | Full details for one activity by ID |
| 10 | `garmin_activity_types` | List all activity types (type IDs and keys) |
| | **Biomarkers & summary** | |
| 11 | `garmin_daily_summary` | One-day wellness: RHR, HR, stress, steps, SpO2, respiration, body battery, calories |
| 12 | `garmin_resting_heart_rate` | Resting heart rate for a date range |
| 13 | `garmin_summary_report` | Comprehensive biomarker + activity report (daily/weekly/biweekly/monthly) |
| | **Delivery** | |
| 14 | `garmin_email_summary` | Generate summary report and send via SMTP email (HTML + plain-text) |
| | **Statistical analysis** | |
| 15 | `garmin_stats` | Run a stats operation on numeric data. `operation`: describe, percentiles, correlation, trend, compare, moving_average, outliers. |
| | **Visualization (matplotlib)** | |
| 16 | `garmin_viz` | Render a chart. `chart_type`: line, bar, scatter, histogram, pie, heatmap, multi_line. Returns file path + base64 PNG. |
| | **Raw API** | |
| 17 | `garmin_connect_api` | Call any Connect API path (GET/POST) |
| | **LIDA / AI visualization (opt-in, requires `LLM_API_KEY`)** | |
| 18 | `garmin_lida_visualize` | AI-driven chart generation -- auto-picks the best chart type |
| 19 | `garmin_lida_goals` | Suggest N visualization goals for a dataset (EDA) |
| 20 | `garmin_lida_explain` | Explain a visualization's code in natural language |

Dates: use `YYYY-MM-DD`; omit end date for "today" where supported.

## SMTP env vars (for delivery tools)

| Variable | Required | Description |
|----------|----------|-------------|
| `SMTP_HOST` | yes | SMTP server (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | no | Port, default `587` (STARTTLS) |
| `SMTP_USER` | yes | Login username / email |
| `SMTP_PASSWORD` | yes | Password or app-password |
| `SMTP_FROM` | no | Sender address (defaults to `SMTP_USER`) |
| `SMTP_TO` | no | Default recipient(s), comma-separated |
| `SMTP_USE_SSL` | no | `"true"` for implicit SSL (port 465); default uses STARTTLS |

## LLM env vars (for LIDA visualization tools -- opt-in)

The 3 LIDA tools (`garmin_lida_*`) are **only registered when `LLM_API_KEY` is set**. If omitted, the server loads with 17 tools instead of 20, reducing context overhead for the AI client.

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `"openai"` | LLM provider for LIDA |
| `LLM_API_BASE` | *(none)* | Custom endpoint -- set to `http://localhost:1234/v1` for LM Studio |
| `LLM_API_KEY` | *(none)* | API key (use `"lm-studio"` for LM Studio). **Setting this enables LIDA tools.** |
| `LLM_MODEL` | `"gpt-4o-mini"` | Model name (for LM Studio: whatever model is loaded) |

Visualization output is saved to `output/viz/` (or `OUTPUT_DIR` env var) and also returned as base64 PNG in the JSON response.
