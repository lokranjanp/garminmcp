"""
Garmin MCP server: comprehensive tools to pull metrics from Garmin Connect via garth.

Auth (in order): existing session tokens → resume from GARTH_SESSION_PATH / ~/.garth
→ login using GARMIN_EMAIL and GARMIN_PASSWORD from MCP config "env".

Author / MCP owner: see pyproject.toml and README.
"""

import json
import os
from datetime import date, datetime, timedelta, timezone
from fastmcp import FastMCP
from .serializers import to_jsonable

garth = None
_client = None


def _garth_client():
    """
    Return garth client, authenticating as needed. Priority:
    1. Already have tokens (from a previous call in this process).
    2. Resume session from GARTH_SESSION_PATH or ~/.garth if that directory exists.
    3. Login using GARMIN_EMAIL and GARMIN_PASSWORD from env (e.g. MCP config.json "env").
    """
    global garth, _client
    if garth is None:
        import garth as _g
        garth = _g
    if _client is None:
        _client = garth.client

    if _client.oauth1_token:
        return _client

    session_path = os.environ.get("GARTH_SESSION_PATH", os.path.expanduser("~/.garth"))
    if os.path.isdir(session_path):
        try:
            garth.resume(session_path)
            if _client.oauth1_token:
                return _client
        except Exception:
            pass

    email = os.environ.get("GARMIN_EMAIL", "").strip()
    password = os.environ.get("GARMIN_PASSWORD", "")
    if email and password:
        try:
            garth.login(email, password)
            os.makedirs(session_path, exist_ok=True)
            garth.save(session_path)
        except Exception:
            raise
        return _client

    return _client


def _ensure_client():
    return _garth_client()


_display_name: str | None = None

def _get_display_name(client) -> str:
    global _display_name
    if _display_name is not None:
        return _display_name
    try:
        from garth import UserProfile
        profile = UserProfile.get(client=client)
        name = getattr(profile, "display_name", None) or getattr(profile, "userName", None)
        if name:
            _display_name = name
            return _display_name
    except Exception:
        pass
    _display_name = client.username
    return _display_name


mcp = FastMCP(
    "Garmin Connect",
    instructions=(
        "Pull metrics from Garmin Connect via the official API (garth). "
        "Auth: set GARTH_SESSION_PATH to resume a saved session, or set "
        "GARMIN_EMAIL and GARMIN_PASSWORD in MCP config env to log in automatically."
    ),
)


# ═══════════════════════════════════════════════════════════════════════════
# 1. Date/time (no auth required)
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# 2. Auth & session
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# 3. User profile / settings
# ═══════════════════════════════════════════════════════════════════════════

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
    try:
        from garth import UserSettings
        settings = UserSettings.get(client=client)
        return json.dumps(to_jsonable(settings), indent=2)
    except Exception:
        try:
            raw = client.connectapi("/userprofile-service/usersettings")
            return json.dumps(to_jsonable(raw), indent=2)
        except Exception as e:
            return json.dumps({"error": str(e)})


# ═══════════════════════════════════════════════════════════════════════════
# 4. garmin_metric – consolidated daily/weekly stats (replaces 9 tools)
# ═══════════════════════════════════════════════════════════════════════════

_METRIC_MAP = {
    ("steps", "daily"): ("garth.DailySteps", "list"),
    ("steps", "weekly"): ("garth.WeeklySteps", "list"),
    ("sleep", "daily"): ("garth.DailySleep", "list"),
    ("stress", "daily"): ("garth.DailyStress", "list"),
    ("stress", "weekly"): ("garth.WeeklyStress", "list"),
    ("hydration", "daily"): ("garth.DailyHydration", "list"),
    ("intensity_minutes", "daily"): ("garth.DailyIntensityMinutes", "list"),
    ("intensity_minutes", "weekly"): ("garth.WeeklyIntensityMinutes", "list"),
    ("hrv", "daily"): ("garth.DailyHRV", "list"),
}


def _resolve_garth_class(dotted: str):
    """Resolve 'garth.ClassName' to the actual class object."""
    import garth as _g
    _, cls_name = dotted.split(".", 1)
    return getattr(_g, cls_name)


@mcp.tool()
def garmin_metric(
    metric: str,
    period: str = "daily",
    end_date: str | None = None,
    count: int = 7,
) -> str:
    """
    Fetch daily or weekly stat series from Garmin Connect.

    metric: "steps", "sleep", "stress", "hydration", "intensity_minutes", or "hrv".
    period: "daily" (default) or "weekly".
    end_date: YYYY-MM-DD (defaults to today/this week).
    count: number of days or weeks to fetch (default 7).

    Examples:
      garmin_metric(metric="steps", period="daily", count=14)
      garmin_metric(metric="stress", period="weekly", count=4)
      garmin_metric(metric="hrv", count=28)
    """
    key = (metric.lower().strip(), period.lower().strip())
    if key not in _METRIC_MAP:
        valid = sorted({f"{m}/{p}" for m, p in _METRIC_MAP})
        return json.dumps({"error": f"Unknown metric/period '{metric}/{period}'. Valid: {valid}"})

    client = _ensure_client()
    cls_path, method = _METRIC_MAP[key]
    cls = _resolve_garth_class(cls_path)
    data = getattr(cls, method)(end=end_date, period=count, client=client)
    return json.dumps(to_jsonable(data), indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# 5. garmin_data – consolidated detailed data (replaces 8 tools)
# ═══════════════════════════════════════════════════════════════════════════

@mcp.tool()
def garmin_data(
    data_type: str,
    day: str | None = None,
    end_date: str | None = None,
    days: int = 7,
) -> str:
    """
    Fetch detailed health data from Garmin Connect.

    data_type: "sleep", "hrv", "weight", "body_battery_events", or "body_battery_stress".
    day: YYYY-MM-DD for single-day data. If omitted, fetches a list.
    end_date: YYYY-MM-DD end of range for list mode (defaults to today).
    days: number of days for list mode (default 7; up to 30 for weight).

    When day is provided: returns detailed data for that single day.
    When day is omitted: returns a list of entries over the date range.

    Note: body_battery_events and body_battery_stress only support single-day mode (day param).

    Examples:
      garmin_data(data_type="sleep", day="2026-02-01")         # single day
      garmin_data(data_type="sleep", days=14)                   # last 14 days
      garmin_data(data_type="weight", end_date="2026-02-01", days=30)
      garmin_data(data_type="body_battery_events", day="2026-02-01")
    """
    dt = data_type.lower().strip()
    client = _ensure_client()

    if dt == "body_battery_events":
        target = day or date.today().isoformat()
        try:
            raw = client.connectapi(f"/wellness-service/wellness/bodyBattery/events/{target}")
        except Exception as e:
            return json.dumps({"error": str(e)})
        if not raw:
            return json.dumps({"message": "No Body Battery events for this day"})
        return json.dumps(to_jsonable(raw), indent=2)

    if dt == "body_battery_stress":
        from garth import DailyBodyBatteryStress
        data = DailyBodyBatteryStress.get(day, client=client)
        if data is None:
            return json.dumps({"message": "No Body Battery/stress data for this day"})
        return json.dumps(to_jsonable(data), indent=2)

    garth_classes = {
        "sleep": "SleepData",
        "hrv": "HRVData",
        "weight": "WeightData",
    }
    if dt not in garth_classes:
        return json.dumps({
            "error": f"Unknown data_type '{data_type}'. "
                     f"Valid: sleep, hrv, weight, body_battery_events, body_battery_stress"
        })

    import garth as _g
    cls = getattr(_g, garth_classes[dt])

    if day:
        data = cls.get(day, client=client)
        if data is None:
            return json.dumps({"message": f"No {dt} data for {day}"})
        return json.dumps(to_jsonable(data), indent=2)

    data = cls.list(end=end_date, days=days, client=client)
    return json.dumps(to_jsonable(data), indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Activities
# ═══════════════════════════════════════════════════════════════════════════

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
def garmin_activity_details(activity_id: int | str) -> str:
    """
    Get full details for one activity by ID (running, cycling, strength, etc.).
    Includes summary (distance, duration, HR, calories, cadence, etc.), splits, and metadata.
    Use garmin_activities first to get activity_id values.
    """
    client = _ensure_client()
    path = f"/activity-service/activity/{activity_id}"
    try:
        result = client.connectapi(path)
    except Exception as e:
        return json.dumps({"error": str(e)})
    if result is None:
        return json.dumps({"message": "No activity found for this ID"})
    return json.dumps(to_jsonable(result), indent=2)


@mcp.tool()
def garmin_activity_types() -> str:
    """List all Garmin activity types (running, cycling, strength_training, etc.) with type IDs and keys."""
    client = _ensure_client()
    path = "/activity-service/activity/activityTypes"
    try:
        result = client.connectapi(path)
    except Exception as e:
        return json.dumps({"error": str(e)})
    if result is None:
        return json.dumps([])
    return json.dumps(to_jsonable(result), indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# 7. Biomarkers & daily summary
# ═══════════════════════════════════════════════════════════════════════════

@mcp.tool()
def garmin_daily_summary(day: str) -> str:
    """
    Get one-day wellness summary (biomarkers): RHR, min/max HR, stress, steps, distance,
    calories, SpO2 (avg/low/high), respiration (avg/low/high), body battery (charged/max/min),
    intensity minutes, floors, sleep summary. day: YYYY-MM-DD.
    """
    client = _ensure_client()
    display = _get_display_name(client)
    path = f"/usersummary-service/usersummary/daily/{display}"
    params = {"calendarDate": day}
    try:
        result = client.connectapi(path, params=params)
    except Exception as e:
        return json.dumps({"error": str(e)})
    if result is None:
        return json.dumps({"message": "No summary for this day"})
    return json.dumps(to_jsonable(result), indent=2)


@mcp.tool()
def garmin_resting_heart_rate(end_date: str | None = None, days: int = 7) -> str:
    """
    Get resting heart rate (RHR) for one or more days. end_date: YYYY-MM-DD or omit for today.
    Returns daily RHR and optional 7-day average. metricId 60 = resting heart rate.
    """
    client = _ensure_client()
    end = date.today() if end_date is None else date.fromisoformat(end_date)
    start = end - timedelta(days=days - 1)
    display = _get_display_name(client)
    path = f"/userstats-service/wellness/daily/{display}"
    params = {
        "fromDate": start.isoformat(),
        "untilDate": end.isoformat(),
        "metricId": "60",
    }
    try:
        result = client.connectapi(path, params=params)
    except Exception as e:
        return json.dumps({"error": str(e)})
    if result is None:
        return json.dumps({"message": "No RHR data for this range"})
    return json.dumps(to_jsonable(result), indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# 8. Aggregate summary report
# ═══════════════════════════════════════════════════════════════════════════

def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _avg(values: list) -> float | None:
    clean = [v for v in values if v is not None]
    return round(sum(clean) / len(clean), 1) if clean else None


def _collect_period_summary(client, start_date: date, end_date: date) -> dict:
    from garth import (
        DailySteps, DailyStress, DailySleep, DailyHRV,
        DailyHydration, DailyIntensityMinutes,
        DailyBodyBatteryStress, WeightData,
    )

    num_days = (end_date - start_date).days + 1

    daily_summaries = []
    for i in range(num_days):
        d = start_date + timedelta(days=i)
        ds = _safe(
            client.connectapi,
            f"/usersummary-service/usersummary/daily/{_get_display_name(client)}",
            params={"calendarDate": d.isoformat()},
        )
        if isinstance(ds, dict):
            daily_summaries.append(ds)

    rhr_vals = [s.get("restingHeartRate") for s in daily_summaries]
    hr_min_vals = [s.get("minHeartRate") for s in daily_summaries]
    hr_max_vals = [s.get("maxHeartRate") for s in daily_summaries]
    spo2_avg_vals = [s.get("averageSpo2") for s in daily_summaries]
    spo2_low_vals = [s.get("lowestSpo2") for s in daily_summaries]
    resp_avg_vals = [s.get("avgWakingRespirationValue") for s in daily_summaries]
    resp_low_vals = [s.get("lowestRespirationValue") for s in daily_summaries]
    resp_high_vals = [s.get("highestRespirationValue") for s in daily_summaries]
    cal_total = [s.get("totalKilocalories") for s in daily_summaries]
    cal_active = [s.get("activeKilocalories") for s in daily_summaries]
    stress_avg_vals = [s.get("averageStressLevel") for s in daily_summaries]
    bb_high_vals = [s.get("bodyBatteryHighestValue") for s in daily_summaries]
    bb_low_vals = [s.get("bodyBatteryLowestValue") for s in daily_summaries]

    steps = _safe(DailySteps.list, end=end_date, period=num_days, client=client) or []
    stress = _safe(DailyStress.list, end=end_date, period=num_days, client=client) or []
    sleep = _safe(DailySleep.list, end=end_date, period=num_days, client=client) or []
    hrv = _safe(DailyHRV.list, end=end_date, period=min(num_days, 28), client=client) or []
    hydration = _safe(DailyHydration.list, end=end_date, period=num_days, client=client) or []
    intensity = _safe(DailyIntensityMinutes.list, end=end_date, period=num_days, client=client) or []
    weights = _safe(WeightData.list, end=end_date, days=num_days, client=client) or []

    total_steps = sum(s.total_steps for s in steps if s.total_steps)
    total_distance_m = sum(s.total_distance for s in steps if s.total_distance)
    sleep_scores = [s.value for s in sleep if s.value is not None]
    hrv_avgs = [h.last_night_avg for h in hrv if h.last_night_avg is not None]
    hydration_ml = [h.value_in_ml for h in hydration if h.value_in_ml is not None]
    moderate_mins = sum(i.moderate_value or 0 for i in intensity)
    vigorous_mins = sum(i.vigorous_value or 0 for i in intensity)

    activities_raw = _safe(
        client.connectapi,
        "/activitylist-service/activities/search/activities",
        params={"start": "0", "limit": "200"},
    )
    activities_in_range = []
    strength_activities = []
    if isinstance(activities_raw, list):
        for a in activities_raw:
            a_start = a.get("startTimeLocal", "")
            if isinstance(a_start, str) and a_start[:10] >= start_date.isoformat() and a_start[:10] <= end_date.isoformat():
                activities_in_range.append(a)
                a_type = (a.get("activityType", {}) or {}).get("typeKey", "")
                if "strength" in a_type.lower():
                    strength_activities.append(a)

    type_counts: dict[str, int] = {}
    for a in activities_in_range:
        t = (a.get("activityType", {}) or {}).get("typeKey", "unknown")
        type_counts[t] = type_counts.get(t, 0) + 1

    strength_details = []
    for sa in strength_activities:
        strength_details.append({
            "activity_id": sa.get("activityId"),
            "name": sa.get("activityName"),
            "date": (sa.get("startTimeLocal") or "")[:10],
            "duration_min": round(sa.get("duration", 0) / 60, 1),
            "calories": sa.get("calories"),
            "avg_hr": sa.get("averageHR"),
            "max_hr": sa.get("maxHR"),
        })

    weight_entries = [{"date": w.calendar_date.isoformat(), "weight_g": w.weight} for w in weights]

    return {
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "days": num_days},
        "heart_rate": {
            "resting_hr_avg": _avg(rhr_vals),
            "hr_min": min((v for v in hr_min_vals if v), default=None),
            "hr_max": max((v for v in hr_max_vals if v), default=None),
        },
        "hrv": {
            "avg_nightly_hrv": _avg(hrv_avgs),
            "min_nightly_hrv": min(hrv_avgs, default=None),
            "max_nightly_hrv": max(hrv_avgs, default=None),
        },
        "stress": {
            "avg_stress_level": _avg(stress_avg_vals),
            "daily_stress_levels": [
                {"date": s.calendar_date.isoformat(), "level": s.overall_stress_level}
                for s in stress
            ],
        },
        "sleep": {
            "avg_sleep_score": _avg(sleep_scores),
            "min_sleep_score": min(sleep_scores, default=None),
            "max_sleep_score": max(sleep_scores, default=None),
        },
        "spo2": {
            "avg_spo2": _avg(spo2_avg_vals),
            "lowest_spo2": min((v for v in spo2_low_vals if v), default=None),
        },
        "respiration": {
            "avg_waking_respiration": _avg(resp_avg_vals),
            "lowest_respiration": min((v for v in resp_low_vals if v), default=None),
            "highest_respiration": max((v for v in resp_high_vals if v), default=None),
        },
        "body_battery": {
            "avg_highest": _avg(bb_high_vals),
            "avg_lowest": _avg(bb_low_vals),
        },
        "steps": {
            "total_steps": total_steps,
            "avg_daily_steps": round(total_steps / num_days) if num_days else 0,
            "total_distance_km": round(total_distance_m / 1000, 1) if total_distance_m else 0,
        },
        "hydration": {
            "avg_daily_ml": _avg(hydration_ml),
        },
        "intensity_minutes": {
            "total_moderate": moderate_mins,
            "total_vigorous": vigorous_mins,
            "total_combined": moderate_mins + vigorous_mins,
        },
        "calories": {
            "avg_daily_total": _avg(cal_total),
            "avg_daily_active": _avg(cal_active),
        },
        "weight": {
            "entries": weight_entries,
            "latest_weight_g": weight_entries[-1]["weight_g"] if weight_entries else None,
        },
        "activities": {
            "total_count": len(activities_in_range),
            "by_type": type_counts,
            "total_duration_min": round(sum(a.get("duration", 0) for a in activities_in_range) / 60, 1),
            "total_calories": round(sum(a.get("calories", 0) or 0 for a in activities_in_range)),
        },
        "strength_training": {
            "session_count": len(strength_activities),
            "sessions": strength_details,
            "total_duration_min": round(sum(s["duration_min"] for s in strength_details), 1),
            "total_calories": sum(s["calories"] or 0 for s in strength_details),
        },
    }


@mcp.tool()
def garmin_summary_report(
    period: str = "weekly",
    end_date: str | None = None,
) -> str:
    """
    Generate a comprehensive summary of all essential biomarkers and activity stats.

    period: "daily" (1 day), "weekly" (7 days), "biweekly" (14 days), or "monthly" (30 days).
    end_date: YYYY-MM-DD (defaults to today).

    Includes: RHR, HRV, stress, sleep score, SpO2, respiration, body battery, steps,
    hydration, intensity minutes, calories, weight, activities breakdown, and
    strength training sessions.
    """
    client = _ensure_client()
    end = date.today() if end_date is None else date.fromisoformat(end_date)
    period_days = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30}
    days = period_days.get(period.lower(), 7)
    start = end - timedelta(days=days - 1)
    summary = _collect_period_summary(client, start, end)
    summary["report_type"] = period.lower()
    return json.dumps(summary, indent=2)


# ═══════════════════════════════════════════════════════════════════════════
# 9. Delivery tools (email)
# ═══════════════════════════════════════════════════════════════════════════

from .delivery import register_delivery_tools
register_delivery_tools(mcp)


# ═══════════════════════════════════════════════════════════════════════════
# 10. Raw Garmin Connect API
# ═══════════════════════════════════════════════════════════════════════════

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


# ═══════════════════════════════════════════════════════════════════════════
# 11. Stats tool (consolidated)
# ═══════════════════════════════════════════════════════════════════════════

from .stats import register_stats_tools
register_stats_tools(mcp)


# ═══════════════════════════════════════════════════════════════════════════
# 12. Visualization tool (consolidated matplotlib)
# ═══════════════════════════════════════════════════════════════════════════

from .visualizers import register_viz_tools
register_viz_tools(mcp)


# ═══════════════════════════════════════════════════════════════════════════
# 13. LIDA tools (opt-in: only registered when LLM_API_KEY is set)
# ═══════════════════════════════════════════════════════════════════════════

if os.environ.get("LLM_API_KEY", "").strip():
    from .lida_viz import register_lida_tools
    register_lida_tools(mcp)


# ═══════════════════════════════════════════════════════════════════════════
# Entrypoint
# ═══════════════════════════════════════════════════════════════════════════

def run():
    print("Starting Garmin MCP server...")
    mcp.run()


if __name__ == "__main__":
    run()
