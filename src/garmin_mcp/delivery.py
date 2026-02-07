"""
Delivery tools – send Garmin summary reports via email (SMTP).

SMTP configuration is read from environment variables (set them in the MCP
config "env" block alongside the Garmin credentials):

    SMTP_HOST      – SMTP server (e.g. smtp.gmail.com)
    SMTP_PORT      – port, default 587 (STARTTLS) or 465 (SSL)
    SMTP_USER      – login username / email
    SMTP_PASSWORD  – login password (use an app-password for Gmail)
    SMTP_FROM      – sender address (defaults to SMTP_USER)
    SMTP_TO        – default recipient(s), comma-separated
    SMTP_USE_SSL   – set to "true" for implicit SSL (port 465); default uses STARTTLS
"""

from __future__ import annotations

import json
import os
import smtplib
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


# ---------------------------------------------------------------------------
# SMTP helpers
# ---------------------------------------------------------------------------

def _smtp_config() -> dict:
    """Read SMTP settings from env. Raises ValueError if essentials are missing."""
    host = os.environ.get("SMTP_HOST", "").strip()
    port = int(os.environ.get("SMTP_PORT", "587"))
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "")
    sender = os.environ.get("SMTP_FROM", "").strip() or user
    default_to = os.environ.get("SMTP_TO", "").strip()
    use_ssl = os.environ.get("SMTP_USE_SSL", "").strip().lower() in ("true", "1", "yes")

    if not host:
        raise ValueError("SMTP_HOST env var is not set")
    if not user or not password:
        raise ValueError("SMTP_USER and SMTP_PASSWORD env vars are required")

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "from": sender,
        "default_to": default_to,
        "use_ssl": use_ssl,
    }


def _send_email(cfg: dict, to: str, subject: str, html_body: str, text_body: str) -> None:
    """Send a multipart (HTML + plain-text) email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["From"] = cfg["from"]
    msg["To"] = to
    msg["Subject"] = subject

    msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    if cfg["use_ssl"]:
        with smtplib.SMTP_SSL(cfg["host"], cfg["port"]) as smtp:
            smtp.login(cfg["user"], cfg["password"])
            smtp.sendmail(cfg["from"], [addr.strip() for addr in to.split(",")], msg.as_string())
    else:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(cfg["user"], cfg["password"])
            smtp.sendmail(cfg["from"], [addr.strip() for addr in to.split(",")], msg.as_string())


# ---------------------------------------------------------------------------
# HTML / plain-text formatters
# ---------------------------------------------------------------------------

_PERIOD_LABELS = {"daily": "Daily", "weekly": "Weekly", "biweekly": "Bi-Weekly", "monthly": "Monthly"}


def _fmt(val, unit: str = "", fallback: str = "N/A") -> str:
    if val is None:
        return fallback
    if isinstance(val, float):
        return f"{val:.1f}{unit}"
    return f"{val}{unit}"


def _render_html(summary: dict) -> str:
    """Build a clean, responsive HTML email from a summary dict."""
    period = summary.get("period", {})
    period_label = _PERIOD_LABELS.get(summary.get("report_type", ""), "Summary")

    def section(title: str, rows: list[tuple[str, str]]) -> str:
        row_html = "".join(
            f'<tr><td style="padding:4px 12px 4px 0;color:#555">{k}</td>'
            f'<td style="padding:4px 0;font-weight:600">{v}</td></tr>'
            for k, v in rows
        )
        return (
            f'<tr><td colspan="2" style="padding:14px 0 6px;font-size:16px;font-weight:700;'
            f'color:#1a73e8;border-bottom:1px solid #e0e0e0">{title}</td></tr>'
            f'{row_html}'
        )

    hr = summary.get("heart_rate", {})
    hrv = summary.get("hrv", {})
    stress = summary.get("stress", {})
    slp = summary.get("sleep", {})
    spo2 = summary.get("spo2", {})
    resp = summary.get("respiration", {})
    bb = summary.get("body_battery", {})
    steps = summary.get("steps", {})
    hyd = summary.get("hydration", {})
    im = summary.get("intensity_minutes", {})
    cal = summary.get("calories", {})
    wt = summary.get("weight", {})
    act = summary.get("activities", {})
    st = summary.get("strength_training", {})

    sections = [
        section("Heart Rate", [
            ("Avg Resting HR", _fmt(hr.get("resting_hr_avg"), " bpm")),
            ("Min HR", _fmt(hr.get("hr_min"), " bpm")),
            ("Max HR", _fmt(hr.get("hr_max"), " bpm")),
        ]),
        section("HRV", [
            ("Avg Nightly HRV", _fmt(hrv.get("avg_nightly_hrv"), " ms")),
            ("Min", _fmt(hrv.get("min_nightly_hrv"), " ms")),
            ("Max", _fmt(hrv.get("max_nightly_hrv"), " ms")),
        ]),
        section("Stress", [
            ("Avg Stress Level", _fmt(stress.get("avg_stress_level"))),
        ]),
        section("Sleep", [
            ("Avg Score", _fmt(slp.get("avg_sleep_score"))),
            ("Min Score", _fmt(slp.get("min_sleep_score"))),
            ("Max Score", _fmt(slp.get("max_sleep_score"))),
        ]),
        section("SpO2", [
            ("Avg SpO2", _fmt(spo2.get("avg_spo2"), "%")),
            ("Lowest", _fmt(spo2.get("lowest_spo2"), "%")),
        ]),
        section("Respiration", [
            ("Avg Waking", _fmt(resp.get("avg_waking_respiration"), " brpm")),
            ("Lowest", _fmt(resp.get("lowest_respiration"), " brpm")),
            ("Highest", _fmt(resp.get("highest_respiration"), " brpm")),
        ]),
        section("Body Battery", [
            ("Avg Daily High", _fmt(bb.get("avg_highest"))),
            ("Avg Daily Low", _fmt(bb.get("avg_lowest"))),
        ]),
        section("Steps & Distance", [
            ("Total Steps", _fmt(steps.get("total_steps"))),
            ("Avg Daily Steps", _fmt(steps.get("avg_daily_steps"))),
            ("Total Distance", _fmt(steps.get("total_distance_km"), " km")),
        ]),
        section("Hydration", [
            ("Avg Daily Intake", _fmt(hyd.get("avg_daily_ml"), " ml")),
        ]),
        section("Intensity Minutes", [
            ("Moderate", _fmt(im.get("total_moderate"), " min")),
            ("Vigorous", _fmt(im.get("total_vigorous"), " min")),
            ("Combined", _fmt(im.get("total_combined"), " min")),
        ]),
        section("Calories", [
            ("Avg Daily Total", _fmt(cal.get("avg_daily_total"), " kcal")),
            ("Avg Daily Active", _fmt(cal.get("avg_daily_active"), " kcal")),
        ]),
        section("Weight", [
            ("Latest", _fmt(
                round(wt["latest_weight_g"] / 1000, 1) if wt.get("latest_weight_g") else None, " kg"
            )),
        ]),
        section("Activities", [
            ("Total", _fmt(act.get("total_count"))),
            ("Duration", _fmt(act.get("total_duration_min"), " min")),
            ("Calories Burned", _fmt(act.get("total_calories"), " kcal")),
            ("By Type", ", ".join(f"{k} ({v})" for k, v in (act.get("by_type") or {}).items()) or "N/A"),
        ]),
        section("Strength Training", [
            ("Sessions", _fmt(st.get("session_count"))),
            ("Total Duration", _fmt(st.get("total_duration_min"), " min")),
            ("Total Calories", _fmt(st.get("total_calories"), " kcal")),
        ]),
    ]

    # per-session strength rows
    strength_sessions_html = ""
    for s in st.get("sessions", []):
        strength_sessions_html += (
            f'<tr><td style="padding:2px 12px 2px 16px;color:#555;font-size:13px">'
            f'{s.get("date", "")} — {s.get("name", "Untitled")}</td>'
            f'<td style="padding:2px 0;font-size:13px">'
            f'{_fmt(s.get("duration_min"), " min")} · '
            f'{_fmt(s.get("calories"), " kcal")} · '
            f'HR {_fmt(s.get("avg_hr"))}/{_fmt(s.get("max_hr"))}'
            f'</td></tr>'
        )

    return f"""\
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#f5f5f5">
<div style="max-width:600px;margin:24px auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 1px 4px rgba(0,0,0,.1)">
  <div style="background:#1a73e8;padding:20px 24px">
    <h1 style="margin:0;color:#fff;font-size:22px">Garmin {period_label} Report</h1>
    <p style="margin:4px 0 0;color:#c6dafc;font-size:14px">{period.get("start","")} to {period.get("end","")} ({period.get("days","")} days)</p>
  </div>
  <div style="padding:8px 24px 24px">
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      {"".join(sections)}
      {strength_sessions_html}
    </table>
  </div>
  <div style="padding:12px 24px;background:#fafafa;border-top:1px solid #e0e0e0;font-size:12px;color:#888;text-align:center">
    Generated by Garmin MCP · data via Garmin Connect
  </div>
</div>
</body></html>"""


def _render_text(summary: dict) -> str:
    """Build a plain-text fallback from a summary dict."""
    period = summary.get("period", {})
    period_label = _PERIOD_LABELS.get(summary.get("report_type", ""), "Summary")
    lines = [
        f"GARMIN {period_label.upper()} REPORT",
        f"{period.get('start','')} to {period.get('end','')} ({period.get('days','')} days)",
        "=" * 52,
    ]

    def add(title: str, rows: list[tuple[str, str]]) -> None:
        lines.append(f"\n--- {title} ---")
        for k, v in rows:
            lines.append(f"  {k:<26} {v}")

    hr = summary.get("heart_rate", {})
    hrv = summary.get("hrv", {})
    stress = summary.get("stress", {})
    slp = summary.get("sleep", {})
    spo2 = summary.get("spo2", {})
    resp = summary.get("respiration", {})
    bb = summary.get("body_battery", {})
    steps = summary.get("steps", {})
    hyd = summary.get("hydration", {})
    im = summary.get("intensity_minutes", {})
    cal = summary.get("calories", {})
    wt = summary.get("weight", {})
    act = summary.get("activities", {})
    st = summary.get("strength_training", {})

    add("Heart Rate", [
        ("Avg Resting HR", _fmt(hr.get("resting_hr_avg"), " bpm")),
        ("Min HR", _fmt(hr.get("hr_min"), " bpm")),
        ("Max HR", _fmt(hr.get("hr_max"), " bpm")),
    ])
    add("HRV", [
        ("Avg Nightly HRV", _fmt(hrv.get("avg_nightly_hrv"), " ms")),
        ("Min", _fmt(hrv.get("min_nightly_hrv"), " ms")),
        ("Max", _fmt(hrv.get("max_nightly_hrv"), " ms")),
    ])
    add("Stress", [("Avg Stress Level", _fmt(stress.get("avg_stress_level")))])
    add("Sleep", [
        ("Avg Score", _fmt(slp.get("avg_sleep_score"))),
        ("Min Score", _fmt(slp.get("min_sleep_score"))),
        ("Max Score", _fmt(slp.get("max_sleep_score"))),
    ])
    add("SpO2", [
        ("Avg SpO2", _fmt(spo2.get("avg_spo2"), "%")),
        ("Lowest", _fmt(spo2.get("lowest_spo2"), "%")),
    ])
    add("Respiration", [
        ("Avg Waking", _fmt(resp.get("avg_waking_respiration"), " brpm")),
        ("Lowest", _fmt(resp.get("lowest_respiration"), " brpm")),
        ("Highest", _fmt(resp.get("highest_respiration"), " brpm")),
    ])
    add("Body Battery", [
        ("Avg Daily High", _fmt(bb.get("avg_highest"))),
        ("Avg Daily Low", _fmt(bb.get("avg_lowest"))),
    ])
    add("Steps & Distance", [
        ("Total Steps", _fmt(steps.get("total_steps"))),
        ("Avg Daily Steps", _fmt(steps.get("avg_daily_steps"))),
        ("Total Distance", _fmt(steps.get("total_distance_km"), " km")),
    ])
    add("Hydration", [("Avg Daily Intake", _fmt(hyd.get("avg_daily_ml"), " ml"))])
    add("Intensity Minutes", [
        ("Moderate", _fmt(im.get("total_moderate"), " min")),
        ("Vigorous", _fmt(im.get("total_vigorous"), " min")),
        ("Combined", _fmt(im.get("total_combined"), " min")),
    ])
    add("Calories", [
        ("Avg Daily Total", _fmt(cal.get("avg_daily_total"), " kcal")),
        ("Avg Daily Active", _fmt(cal.get("avg_daily_active"), " kcal")),
    ])
    add("Weight", [
        ("Latest", _fmt(
            round(wt["latest_weight_g"] / 1000, 1) if wt.get("latest_weight_g") else None, " kg"
        )),
    ])
    add("Activities", [
        ("Total", _fmt(act.get("total_count"))),
        ("Duration", _fmt(act.get("total_duration_min"), " min")),
        ("Calories Burned", _fmt(act.get("total_calories"), " kcal")),
        ("By Type", ", ".join(f"{k} ({v})" for k, v in (act.get("by_type") or {}).items()) or "N/A"),
    ])
    add("Strength Training", [
        ("Sessions", _fmt(st.get("session_count"))),
        ("Total Duration", _fmt(st.get("total_duration_min"), " min")),
        ("Total Calories", _fmt(st.get("total_calories"), " kcal")),
    ])
    for s in st.get("sessions", []):
        lines.append(
            f"    {s.get('date','')} — {s.get('name','Untitled')}: "
            f"{_fmt(s.get('duration_min'),' min')} · {_fmt(s.get('calories'),' kcal')} · "
            f"HR {_fmt(s.get('avg_hr'))}/{_fmt(s.get('max_hr'))}"
        )

    lines.append("\n-- Generated by Garmin MCP --")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_delivery_tools(mcp_instance) -> None:
    """Register delivery-suite tools on the given FastMCP instance."""

    @mcp_instance.tool()
    def garmin_email_summary(
        period: str = "weekly",
        end_date: str | None = None,
        to: str | None = None,
        subject: str | None = None,
    ) -> str:
        """
        Generate a Garmin summary report and email it via SMTP.

        period: "daily", "weekly", "biweekly", or "monthly" (default: weekly).
        end_date: YYYY-MM-DD (defaults to today).
        to: recipient email(s), comma-separated (defaults to SMTP_TO env var).
        subject: custom subject line (auto-generated if omitted).

        Requires SMTP env vars: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD.
        Optional: SMTP_FROM (defaults to SMTP_USER), SMTP_TO (default recipient),
        SMTP_USE_SSL ("true" for port-465 implicit SSL; default is STARTTLS).

        The email contains a formatted HTML report (with plain-text fallback) covering
        all biomarkers: HR, HRV, stress, sleep, SpO2, respiration, body battery,
        steps, hydration, intensity minutes, calories, weight, activities, and
        strength training sessions.

        FOCUS MORE ON STRENGTH AND CARDIO BIO-MARKERS IF POSSIBLE.
        """
        # -- import heavy helpers lazily to avoid circular imports --
        from .server import _collect_period_summary, _ensure_client

        # 1. Build summary
        client = _ensure_client()
        end = date.today() if end_date is None else date.fromisoformat(end_date)
        period_days = {"daily": 1, "weekly": 7, "biweekly": 14, "monthly": 30}
        days = period_days.get(period.lower(), 7)
        start = end - timedelta(days=days - 1)
        summary = _collect_period_summary(client, start, end)
        summary["report_type"] = period.lower()

        # 2. Resolve SMTP config
        try:
            cfg = _smtp_config()
        except ValueError as exc:
            return json.dumps({"error": str(exc), "hint": "Set SMTP_* env vars in MCP config."})

        recipient = (to or cfg["default_to"]).strip()
        if not recipient:
            return json.dumps({"error": "No recipient. Pass 'to' or set SMTP_TO env var."})

        period_label = _PERIOD_LABELS.get(period.lower(), "Summary")
        email_subject = subject or (
            f"Garmin {period_label} Report: "
            f"{summary['period']['start']} – {summary['period']['end']}"
        )

        # 3. Render
        html_body = _render_html(summary)
        text_body = _render_text(summary)

        # 4. Send
        try:
            _send_email(cfg, recipient, email_subject, html_body, text_body)
        except Exception as exc:
            return json.dumps({
                "error": f"SMTP send failed: {exc}",
                "hint": "Check SMTP_* env vars, network access, and credentials.",
            })

        return json.dumps({
            "status": "sent",
            "to": recipient,
            "subject": email_subject,
            "period": summary["period"],
            "report_type": period.lower(),
        }, indent=2)
