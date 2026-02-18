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
| **Aggregate reports** | |
| `garmin_summary_report` | Comprehensive biomarker + activity report (daily / weekly / biweekly / monthly) |
| **Delivery tools** | |
| `garmin_email_summary` | Generate summary report and send via SMTP email (HTML + plain-text) |
| **Stats tools** | |
| `garmin_stats_describe` | Descriptive stats: mean, median, mode, stdev, Q1/Q3, IQR, skewness, kurtosis |
| `garmin_stats_percentiles` | Compute arbitrary percentiles (default: 5/10/25/50/75/90/95) |
| `garmin_stats_correlation` | Pearson or Spearman correlation between two metric samples |
| `garmin_stats_trend` | Linear trend: slope, R², direction, predicted next value |
| `garmin_stats_compare` | Compare two samples: diff, % change, Cohen's d effect size |
| `garmin_stats_moving_average` | Simple moving average with configurable window (default 7) |
| `garmin_stats_outliers` | Outlier detection via IQR fences or z-score |
| **Visualizers (matplotlib)** | |
| `garmin_viz_line` | Line chart (e.g. daily steps over time) |
| `garmin_viz_bar` | Bar chart (e.g. activity type counts) |
| `garmin_viz_scatter` | Scatter plot with trend line (e.g. steps vs sleep) |
| `garmin_viz_histogram` | Histogram / distribution (e.g. HRV spread) |
| `garmin_viz_pie` | Pie chart (e.g. activity type %) |
| `garmin_viz_heatmap` | Heatmap from a 2-D matrix (e.g. weekly stress grid) |
| `garmin_viz_multi_line` | Overlay multiple series on one chart |
| **Visualizers (LIDA / AI)** | |
| `garmin_lida_visualize` | AI-driven chart generation -- auto-picks the best chart type |
| `garmin_lida_goals` | Suggest N visualization goals for a dataset (EDA) |
| `garmin_lida_explain` | Explain a visualization's code in natural language |
| **Raw API** | |
| `garmin_connect_api` | Call any Connect API path (GET/POST) |

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

## LLM env vars (for LIDA visualization tools)

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `"openai"` | LLM provider for LIDA |
| `LLM_API_BASE` | *(none)* | Custom endpoint -- set to `http://localhost:1234/v1` for LM Studio |
| `LLM_API_KEY` | *(none)* | API key (use `"lm-studio"` for LM Studio) |
| `LLM_MODEL` | `"gpt-4o-mini"` | Model name (for LM Studio: whatever model is loaded) |

Visualization output is saved to `output/viz/` and also returned as base64 PNG in the JSON response.
