"""
Garmin MCP server: comprehensive tools to pull metrics from Garmin Connect via garth.
Requires an authenticated session (login once, then resume_session or set GARTH_SESSION_PATH).
"""

import json
import os
from datetime import date, datetime, timezone

from fastmcp import FastMCP

from .serializers import to_jsonable

# Lazy garth import so we don't require auth at import time
garth = None
_client = None


def _garth_client():
    """Return garth client, resuming session from env or default path if needed."""
    global garth, _client
    if garth is None:
        import garth as _g
        garth = _g
    if _client is None:
        _client = garth.client
    # Resume session if we have a path and client has no tokens
    if not _client.oauth1_token:
        path = os.environ.get("GARTH_SESSION_PATH", os.path.expanduser("~/.garth"))
        if os.path.isdir(path):
            garth.resume(path)
    return _client


def _ensure_client():
    """Ensure garth client is configured (resume from default path if possible)."""
    return _garth_client()


# ---------------------------------------------------------------------------
# MCP app
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "Garmin Connect",
    instructions="Pull metrics from Garmin Connect via the official API (garth). Login once, then use resume_session or set GARTH_SESSION_PATH.",
)


# ---------------------------------------------------------------------------
# Date/time (no auth required)
# ---------------------------------------------------------------------------

@mcp.tool()
def garmin_current_datetime() -> str:
    """
    Return current date and time variables (local and UTC). Use for building date ranges
    or passing today's date to other Garmin tools (e.g. YYYY-MM-DD for day/sleep/weight).
    """
    now_utc = datetime.now(timezone.utc)
    now_local = datetime.now().astimezone()
    return json.dumps({
        "date_iso": now_local.date().isoformat(),
        "datetime_iso_local": now_local.isoformat(),
        "datetime_iso_utc": now_utc.isoformat(),
        "year": now_local.year,
        "month": now_local.month,
        "day": now_local.day,
        "weekday": now_local.strftime("%A"),
        "timezone": str(now_local.tzinfo),
    }, indent=2)


# ---------------------------------------------------------------------------
# Auth & session
# ---------------------------------------------------------------------------

@mcp.tool()
def garmin_login(email: str, password: str, session_path: str = "") -> str:
    """
    Log in to Garmin Connect with email and password. Saves the session to the given path
    (default: ~/.garth) so you can use resume_session later without logging in again.
    """
    _ensure_client()
    path = session_path or os.path.expanduser("~/.garth")
    garth.login(email, password)
    garth.save(path)
    return json.dumps({"status": "ok", "message": f"Logged in and session saved to {path}"})


@mcp.tool()
def garmin_resume_session(session_path: str = "") -> str:
    """
    Resume a previously saved Garmin session from disk. Use this (or set GARTH_SESSION_PATH)
    before calling other tools so they are authenticated. Default path: ~/.garth.
    """
    path = session_path or os.environ.get("GARTH_SESSION_PATH", os.path.expanduser("~/.garth"))
    _garth_client()
    garth.resume(path)
    return json.dumps({"status": "ok", "message": f"Session resumed from {path}"})


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

@mcp.tool()
def garmin_user_profile() -> str:
    """Get the current user's Garmin Connect profile (display name, timezone, activities, etc.)."""
    client = _ensure_client()
    from garth import UserProfile
    profile = UserProfile.get(client=client)
    return json.dumps(to_jsonable(profile), indent=2)


@mcp.tool()
def garmin_user_settings() -> str:
    """Get the current user's Garmin Connect settings (units, preferences, etc.)."""
    client = _ensure_client()
    from garth import UserSettings
    settings = UserSettings.get(client=client)
    return json.dumps(to_jsonable(settings), indent=2)


# ---------------------------------------------------------------------------
# Stats: steps, sleep, stress, hydration, intensity minutes, HRV
# ---------------------------------------------------------------------------

@mcp.tool()
def garmin_daily_steps(end_date: str | None = None, days: int = 7) -> str:
    """Get daily steps (and distance, step goal) for the last N days. end_date: YYYY-MM-DD or omit for today."""
    client = _ensure_client()
    from garth import DailySteps
    data = DailySteps.list(end=end_date, period=days, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_weekly_steps(end_date: str | None = None, weeks: int = 4) -> str:
    """Get weekly steps summary for the last N weeks. end_date: YYYY-MM-DD or omit for this week."""
    client = _ensure_client()
    from garth import WeeklySteps
    data = WeeklySteps.list(end=end_date, period=weeks, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_daily_sleep_stats(end_date: str | None = None, days: int = 7) -> str:
    """Get daily sleep score/values for the last N days (summary stats, not full sleep data)."""
    client = _ensure_client()
    from garth import DailySleep
    data = DailySleep.list(end=end_date, period=days, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_daily_stress(end_date: str | None = None, days: int = 7) -> str:
    """Get daily stress (overall level and durations by level) for the last N days."""
    client = _ensure_client()
    from garth import DailyStress
    data = DailyStress.list(end=end_date, period=days, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_weekly_stress(end_date: str | None = None, weeks: int = 4) -> str:
    """Get weekly stress summary for the last N weeks."""
    client = _ensure_client()
    from garth import WeeklyStress
    data = WeeklyStress.list(end=end_date, period=weeks, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_daily_hydration(end_date: str | None = None, days: int = 7) -> str:
    """Get daily hydration (value and goal in ml) for the last N days."""
    client = _ensure_client()
    from garth import DailyHydration
    data = DailyHydration.list(end=end_date, period=days, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_daily_intensity_minutes(end_date: str | None = None, days: int = 7) -> str:
    """Get daily intensity minutes (moderate/vigorous and weekly goal) for the last N days."""
    client = _ensure_client()
    from garth import DailyIntensityMinutes
    data = DailyIntensityMinutes.list(end=end_date, period=days, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_weekly_intensity_minutes(end_date: str | None = None, weeks: int = 4) -> str:
    """Get weekly intensity minutes for the last N weeks."""
    client = _ensure_client()
    from garth import WeeklyIntensityMinutes
    data = WeeklyIntensityMinutes.list(end=end_date, period=weeks, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_daily_hrv(end_date: str | None = None, days: int = 28) -> str:
    """Get daily HRV (heart rate variability) summary for the last N days."""
    client = _ensure_client()
    from garth import DailyHRV
    data = DailyHRV.list(end=end_date, period=days, client=client)
    return json.dumps(to_jsonable(data), indent=2)


# ---------------------------------------------------------------------------
# Data: sleep, HRV, weight, body battery
# ---------------------------------------------------------------------------

@mcp.tool()
def garmin_sleep_data(day: str) -> str:
    """Get full sleep data for a single day (sleep stages, movement, scores). day: YYYY-MM-DD."""
    client = _ensure_client()
    from garth import SleepData
    data = SleepData.get(day, client=client)
    if data is None:
        return json.dumps({"message": "No sleep data for this day"})
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_sleep_data_list(end_date: str | None = None, days: int = 7) -> str:
    """List full sleep data for the last N days. end_date: YYYY-MM-DD or omit for today."""
    client = _ensure_client()
    from garth import SleepData
    data = SleepData.list(end=end_date, days=days, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_hrv_data(day: str) -> str:
    """Get full HRV data for a single day (readings, baseline, summary). day: YYYY-MM-DD."""
    client = _ensure_client()
    from garth import HRVData
    data = HRVData.get(day, client=client)
    if data is None:
        return json.dumps({"message": "No HRV data for this day"})
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_hrv_data_list(end_date: str | None = None, days: int = 7) -> str:
    """List full HRV data for the last N days."""
    client = _ensure_client()
    from garth import HRVData
    data = HRVData.list(end=end_date, days=days, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_weight(day: str) -> str:
    """Get weight (and optional body composition) for a single day. day: YYYY-MM-DD."""
    client = _ensure_client()
    from garth import WeightData
    data = WeightData.get(day, client=client)
    if data is None:
        return json.dumps({"message": "No weight data for this day"})
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_weight_list(end_date: str | None = None, days: int = 30) -> str:
    """List weight entries for the last N days."""
    client = _ensure_client()
    from garth import WeightData
    data = WeightData.list(end=end_date, days=days, client=client)
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_body_battery_events(day: str | None = None) -> str:
    """Get Body Battery events for a day (legacy events, often sleep-only). day: YYYY-MM-DD or omit for today."""
    client = _ensure_client()
    from garth import BodyBatteryData
    data = BodyBatteryData.get(day, client=client)
    if not data:
        return json.dumps({"message": "No Body Battery events for this day"})
    return json.dumps(to_jsonable(data), indent=2)


@mcp.tool()
def garmin_daily_body_battery_stress(day: str | None = None) -> str:
    """Get full daily Body Battery and stress data for a day (values over time). day: YYYY-MM-DD or omit for today."""
    client = _ensure_client()
    from garth import DailyBodyBatteryStress
    data = DailyBodyBatteryStress.get(day, client=client)
    if data is None:
        return json.dumps({"message": "No Body Battery/stress data for this day"})
    return json.dumps(to_jsonable(data), indent=2)


# ---------------------------------------------------------------------------
# Activities & raw API
# ---------------------------------------------------------------------------

@mcp.tool()
def garmin_activities(start: int = 0, limit: int = 20) -> str:
    """
    List activities from Garmin Connect. start: index to start from, limit: max number to return.
    Returns activity IDs, names, types, start time, duration, distance, etc.
    """
    client = _ensure_client()
    path = "/activitylist-service/activities/search/activities"
    params = {"start": str(start), "limit": str(limit)}
    try:
        result = client.connectapi(path, params=params)
    except Exception as e:
        return json.dumps({"error": str(e), "hint": "Ensure you are logged in and have activities."})
    if result is None:
        return json.dumps([])
    if isinstance(result, list):
        activities = result
    elif isinstance(result, dict) and "activities" in result:
        activities = result["activities"]
    else:
        activities = result if isinstance(result, list) else [result]
    return json.dumps(to_jsonable(activities), indent=2)


@mcp.tool()
def garmin_connect_api(path: str, method: str = "GET", body: str | None = None) -> str:
    """
    Call the Garmin Connect API at an arbitrary path. Use for endpoints not wrapped by other tools.
    path: e.g. /userprofile-service/socialProfile or /activitylist-service/...
    method: GET or POST. body: optional JSON string for POST.
    """
    client = _ensure_client()
    kwargs = {}
    if body:
        try:
            kwargs["json"] = json.loads(body)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON body: {e}"})
    try:
        result = client.connectapi(path, method=method.upper(), **kwargs)
    except Exception as e:
        return json.dumps({"error": str(e)})
    if result is None:
        return json.dumps({"result": None})
    return json.dumps(to_jsonable(result), indent=2)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

def run():
    mcp.run()


if __name__ == "__main__":
    run()
