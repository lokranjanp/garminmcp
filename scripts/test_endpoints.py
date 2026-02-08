#!/usr/bin/env python3
"""
Standalone test harness for all garth / Garmin Connect endpoints used by the MCP server.

Authenticates via garth (saved session or GARMIN_EMAIL/GARMIN_PASSWORD env vars),
then exercises every endpoint one-by-one, printing a pass/fail table and sample payloads.

Usage:
    # Resume saved session at ~/.garth (or GARTH_SESSION_PATH)
    python scripts/test_endpoints.py

    # Login via env
    GARMIN_EMAIL=you@example.com GARMIN_PASSWORD=secret python scripts/test_endpoints.py

    # Show full JSON payloads (default: truncated preview)
    python scripts/test_endpoints.py --verbose

    # Test a single endpoint by name
    python scripts/test_endpoints.py --only daily_steps

    # List all available test names
    python scripts/test_endpoints.py --list
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

TODAY = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def to_jsonable(obj: Any) -> Any:
    """Recursively convert objects to JSON-serializable form."""
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    if isinstance(obj, list):
        return [to_jsonable(x) for x in obj]
    if isinstance(obj, dict):
        return {k: to_jsonable(v) for k, v in obj.items()}
    if hasattr(obj, "model_dump"):
        return to_jsonable(obj.model_dump())
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)}
    return str(obj)


def preview(obj: Any, max_chars: int = 300) -> str:
    """JSON preview, truncated."""
    text = json.dumps(to_jsonable(obj), indent=2, default=str)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"\n  ... ({len(text)} chars total)"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

def authenticate():
    """Authenticate garth and return the client."""
    import garth

    session_path = os.environ.get("GARTH_SESSION_PATH", os.path.expanduser("~/.garth"))

    # Try resume first
    if os.path.isdir(session_path):
        try:
            garth.resume(session_path)
            if garth.client.oauth1_token:
                print(f"{GREEN}[auth]{RESET} Resumed session from {session_path}")
                return garth, garth.client
        except Exception:
            pass

    # Fall back to env login
    email = os.environ.get("GARMIN_EMAIL", "").strip()
    password = os.environ.get("GARMIN_PASSWORD", "")
    if email and password:
        print(f"{CYAN}[auth]{RESET} Logging in as {email} ...")
        garth.login(email, password)
        os.makedirs(session_path, exist_ok=True)
        garth.save(session_path)
        print(f"{GREEN}[auth]{RESET} Logged in and session saved to {session_path}")
        return garth, garth.client

    print(f"{RED}[auth]{RESET} No saved session and no GARMIN_EMAIL/GARMIN_PASSWORD set.")
    sys.exit(1)


# ---------------------------------------------------------------------------
# Test definitions – each returns (label, data)
# ---------------------------------------------------------------------------

def _tests(garth_mod, client):
    """Return an ordered dict of test_name -> (description, callable)."""
    from garth import (
        UserProfile, UserSettings,
        DailySteps, WeeklySteps,
        DailySleep, DailyStress, WeeklyStress,
        DailyHydration, DailyIntensityMinutes, WeeklyIntensityMinutes,
        DailyHRV,
        SleepData, HRVData, WeightData,
        BodyBatteryData, DailyBodyBatteryStress,
    )

    tests: dict[str, tuple[str, Any]] = {}

    # ── User ────────────────────────────────────────────────────────────
    tests["user_profile"] = (
        "UserProfile.get()",
        lambda: UserProfile.get(client=client),
    )
    tests["user_settings"] = (
        "UserSettings.get()",
        lambda: UserSettings.get(client=client),
    )

    # ── Stats classes ───────────────────────────────────────────────────
    tests["daily_steps"] = (
        "DailySteps.list(period=3)",
        lambda: DailySteps.list(period=3, client=client),
    )
    tests["weekly_steps"] = (
        "WeeklySteps.list(period=2)",
        lambda: WeeklySteps.list(period=2, client=client),
    )
    tests["daily_sleep_stats"] = (
        "DailySleep.list(period=3)",
        lambda: DailySleep.list(period=3, client=client),
    )
    tests["daily_stress"] = (
        "DailyStress.list(period=3)",
        lambda: DailyStress.list(period=3, client=client),
    )
    tests["weekly_stress"] = (
        "WeeklyStress.list(period=2)",
        lambda: WeeklyStress.list(period=2, client=client),
    )
    tests["daily_hydration"] = (
        "DailyHydration.list(period=3)",
        lambda: DailyHydration.list(period=3, client=client),
    )
    tests["daily_intensity_minutes"] = (
        "DailyIntensityMinutes.list(period=3)",
        lambda: DailyIntensityMinutes.list(period=3, client=client),
    )
    tests["weekly_intensity_minutes"] = (
        "WeeklyIntensityMinutes.list(period=2)",
        lambda: WeeklyIntensityMinutes.list(period=2, client=client),
    )
    tests["daily_hrv"] = (
        "DailyHRV.list(period=3)",
        lambda: DailyHRV.list(period=3, client=client),
    )

    # ── Data classes ────────────────────────────────────────────────────
    tests["sleep_data"] = (
        f"SleepData.get('{YESTERDAY}')",
        lambda: SleepData.get(YESTERDAY, client=client),
    )
    tests["sleep_data_list"] = (
        "SleepData.list(days=3)",
        lambda: SleepData.list(days=3, client=client),
    )
    tests["hrv_data"] = (
        f"HRVData.get('{YESTERDAY}')",
        lambda: HRVData.get(YESTERDAY, client=client),
    )
    tests["hrv_data_list"] = (
        "HRVData.list(days=3)",
        lambda: HRVData.list(days=3, client=client),
    )
    tests["weight_data"] = (
        f"WeightData.get('{TODAY}')",
        lambda: WeightData.get(TODAY, client=client),
    )
    tests["weight_data_list"] = (
        "WeightData.list(days=7)",
        lambda: WeightData.list(days=7, client=client),
    )
    tests["body_battery_events"] = (
        f"BodyBatteryData.get('{YESTERDAY}')",
        lambda: BodyBatteryData.get(YESTERDAY, client=client),
    )
    tests["daily_body_battery_stress"] = (
        f"DailyBodyBatteryStress.get('{YESTERDAY}')",
        lambda: DailyBodyBatteryStress.get(YESTERDAY, client=client),
    )

    # ── connectapi: wellness summary ────────────────────────────────────
    tests["daily_summary_api"] = (
        f"connectapi usersummary/daily ('{YESTERDAY}')",
        lambda: client.connectapi(
            f"/usersummary-service/usersummary/daily/{client.username}",
            params={"calendarDate": YESTERDAY},
        ),
    )

    # ── connectapi: resting heart rate ──────────────────────────────────
    tests["resting_hr_api"] = (
        "connectapi userstats/wellness (RHR, 7d)",
        lambda: client.connectapi(
            f"/userstats-service/wellness/daily/{client.username}",
            params={
                "fromDate": (date.today() - timedelta(days=6)).isoformat(),
                "untilDate": TODAY,
                "metricId": "60",
            },
        ),
    )

    # ── connectapi: activities ──────────────────────────────────────────
    tests["activities_list_api"] = (
        "connectapi activitylist-service (limit=5)",
        lambda: client.connectapi(
            "/activitylist-service/activities/search/activities",
            params={"start": "0", "limit": "5"},
        ),
    )
    tests["activity_types_api"] = (
        "connectapi activity-service/activityTypes",
        lambda: client.connectapi("/activity-service/activityTypes"),
    )

    # activity details – needs an activity ID from the list above, so we
    # fetch one dynamically
    def _activity_detail():
        acts = client.connectapi(
            "/activitylist-service/activities/search/activities",
            params={"start": "0", "limit": "1"},
        )
        if not acts:
            return {"skip": "No activities found to test detail endpoint"}
        aid = acts[0].get("activityId")
        return client.connectapi(f"/activity-service/activity/{aid}")

    tests["activity_detail_api"] = (
        "connectapi activity-service/activity/{id} (latest)",
        _activity_detail,
    )

    return tests


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_tests(garth_mod, client, *, names: list[str] | None = None, verbose: bool = False):
    all_tests = _tests(garth_mod, client)

    if names:
        selected = {n: all_tests[n] for n in names if n in all_tests}
        missing = [n for n in names if n not in all_tests]
        if missing:
            print(f"{YELLOW}[warn]{RESET} Unknown tests: {', '.join(missing)}")
    else:
        selected = all_tests

    results: list[tuple[str, str, str, str | None]] = []  # (name, desc, status, detail)
    total = len(selected)

    print(f"\n{BOLD}Running {total} endpoint tests ...{RESET}\n")

    for idx, (name, (desc, fn)) in enumerate(selected.items(), 1):
        tag = f"[{idx}/{total}]"
        print(f"{CYAN}{tag}{RESET} {name}: {desc} ", end="", flush=True)
        try:
            data = fn()
            if data is None:
                status = "EMPTY"
                detail = "(returned None – possibly no data for this period)"
                print(f"{YELLOW}EMPTY{RESET}")
            else:
                status = "PASS"
                detail = preview(data) if not verbose else json.dumps(to_jsonable(data), indent=2, default=str)
                print(f"{GREEN}PASS{RESET}")
        except Exception as exc:
            status = "FAIL"
            detail = f"{type(exc).__name__}: {exc}"
            if verbose:
                detail += "\n" + traceback.format_exc()
            print(f"{RED}FAIL{RESET}  ({type(exc).__name__})")

        results.append((name, desc, status, detail))

        if verbose and detail:
            for line in detail.split("\n"):
                print(f"    {line}")
            print()

    # ── Summary table ───────────────────────────────────────────────────
    passed = sum(1 for *_, s, _ in results if s == "PASS")
    empty = sum(1 for *_, s, _ in results if s == "EMPTY")
    failed = sum(1 for *_, s, _ in results if s == "FAIL")

    print(f"\n{'=' * 60}")
    print(f"{BOLD}Results: {GREEN}{passed} passed{RESET}, {YELLOW}{empty} empty{RESET}, {RED}{failed} failed{RESET}  (total {total})")
    print(f"{'=' * 60}")

    if failed:
        print(f"\n{RED}{BOLD}Failed endpoints:{RESET}")
        for name, desc, status, detail in results:
            if status == "FAIL":
                print(f"  {RED}x{RESET} {name}: {detail}")

    if empty:
        print(f"\n{YELLOW}Empty endpoints (no data, but API reachable):{RESET}")
        for name, desc, status, detail in results:
            if status == "EMPTY":
                print(f"  - {name}")

    print()
    return 0 if failed == 0 else 1


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Test all garth / Garmin Connect endpoints outside the MCP.",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Print full JSON payloads for each endpoint",
    )
    parser.add_argument(
        "--only", nargs="+", metavar="NAME",
        help="Run only the specified test(s) by name",
    )
    parser.add_argument(
        "--list", "-l", action="store_true",
        help="List all available test names and exit",
    )
    args = parser.parse_args()

    # For --list we still need garth imported but not authenticated
    if args.list:
        # Fake client just to enumerate test names
        import garth
        print(f"\n{BOLD}Available test endpoints:{RESET}\n")
        try:
            all_tests = _tests(garth, garth.client)
        except Exception:
            # Some garth classes may fail to import without auth; build list from source
            all_tests = _tests.__code__.co_consts  # fallback
            print("  (could not enumerate – authenticate first)")
            return 0
        for name, (desc, _) in all_tests.items():
            print(f"  {CYAN}{name:<30}{RESET} {desc}")
        print()
        return 0

    garth_mod, client = authenticate()
    return run_tests(garth_mod, client, names=args.only, verbose=args.verbose)


if __name__ == "__main__":
    sys.exit(main())
