"""
Stats tool -- single statistical-analysis endpoint for Garmin metric samples.

Accepts an operation name and numeric data, performs the requested analysis,
and returns the result as JSON.

Depends on: numpy (added to project dependencies).
"""

from __future__ import annotations

import json
import statistics
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _clean(values: list) -> list[float]:
    out: list[float] = []
    for v in values:
        if v is None:
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def _is_numeric(v: Any) -> bool:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return True
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _require_min(clean: list[float], n: int, label: str = "values") -> str | None:
    if len(clean) < n:
        return json.dumps({"error": f"Need at least {n} numeric {label}, got {len(clean)}."})
    return None


def _safe_mode(vals: list[float]) -> float | str:
    try:
        return statistics.mode(vals)
    except statistics.StatisticsError:
        return "no unique mode"


# ---------------------------------------------------------------------------
# Operation implementations
# ---------------------------------------------------------------------------

def _op_describe(values, **_kw) -> str:
    clean = _clean(values)
    err = _require_min(clean, 1)
    if err:
        return err
    arr = np.array(clean)
    q1, q3 = float(np.percentile(arr, 25)), float(np.percentile(arr, 75))
    n = len(clean)
    result: dict[str, Any] = {
        "count": n,
        "mean": round(float(np.mean(arr)), 4),
        "median": round(float(np.median(arr)), 4),
        "mode": _safe_mode(clean),
        "std_dev": round(float(np.std(arr, ddof=1)), 4) if n > 1 else 0.0,
        "variance": round(float(np.var(arr, ddof=1)), 4) if n > 1 else 0.0,
        "min": round(float(np.min(arr)), 4),
        "max": round(float(np.max(arr)), 4),
        "range": round(float(np.ptp(arr)), 4),
        "q1": round(q1, 4),
        "q3": round(q3, 4),
        "iqr": round(q3 - q1, 4),
    }
    if n >= 3:
        mean = np.mean(arr)
        std = np.std(arr, ddof=1)
        if std > 0:
            skew = float(np.mean(((arr - mean) / std) ** 3))
            kurt = float(np.mean(((arr - mean) / std) ** 4) - 3)
            result["skewness"] = round(skew, 4)
            result["kurtosis"] = round(kurt, 4)
    return json.dumps(result, indent=2)


def _op_percentiles(values, **kw) -> str:
    clean = _clean(values)
    err = _require_min(clean, 1)
    if err:
        return err
    ptiles = kw.get("percentiles") or [5, 10, 25, 50, 75, 90, 95]
    arr = np.array(clean)
    result = {
        f"p{int(p) if p == int(p) else p}": round(float(np.percentile(arr, p)), 4)
        for p in ptiles
    }
    result["count"] = len(clean)
    return json.dumps(result, indent=2)


def _op_correlation(values, **kw) -> str:
    y = kw.get("y") or []
    method = kw.get("method", "pearson")
    pairs = [
        (float(a), float(b))
        for a, b in zip(values, y)
        if a is not None and b is not None and _is_numeric(a) and _is_numeric(b)
    ]
    if len(pairs) < 3:
        return json.dumps({"error": "Need at least 3 paired numeric values for correlation."})
    ax = np.array([p[0] for p in pairs])
    ay = np.array([p[1] for p in pairs])
    if method.lower() == "spearman":
        ax_ranks = np.argsort(np.argsort(ax)).astype(float)
        ay_ranks = np.argsort(np.argsort(ay)).astype(float)
        r = float(np.corrcoef(ax_ranks, ay_ranks)[0, 1])
    else:
        r = float(np.corrcoef(ax, ay)[0, 1])
    abs_r = abs(r)
    strength = "strong" if abs_r >= 0.8 else "moderate" if abs_r >= 0.5 else "weak" if abs_r >= 0.3 else "negligible"
    direction = "positive" if r > 0 else "negative" if r < 0 else "none"
    return json.dumps({
        "method": method.lower(), "r": round(r, 6), "r_squared": round(r ** 2, 6),
        "strength": strength, "direction": direction,
        "interpretation": f"{strength} {direction} correlation", "sample_size": len(pairs),
    }, indent=2)


def _op_trend(values, **kw) -> str:
    labels = kw.get("labels")
    clean = _clean(values)
    err = _require_min(clean, 3, "values for trend")
    if err:
        return err
    arr = np.array(clean)
    x = np.arange(len(arr), dtype=float)
    coeffs = np.polyfit(x, arr, 1)
    slope, intercept = float(coeffs[0]), float(coeffs[1])
    predicted = np.polyval(coeffs, x)
    ss_res = float(np.sum((arr - predicted) ** 2))
    ss_tot = float(np.sum((arr - np.mean(arr)) ** 2))
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    direction = "stable" if r_squared < 0.1 else ("increasing" if slope > 0 else "decreasing")
    next_val = float(np.polyval(coeffs, len(arr)))
    result: dict[str, Any] = {
        "slope_per_unit": round(slope, 6), "intercept": round(intercept, 4),
        "r_squared": round(r_squared, 6), "direction": direction,
        "predicted_next": round(next_val, 4), "sample_size": len(clean),
        "first_value": clean[0], "last_value": clean[-1],
        "total_change": round(clean[-1] - clean[0], 4),
        "pct_change": round(((clean[-1] - clean[0]) / clean[0]) * 100, 2) if clean[0] != 0 else None,
    }
    if labels and len(labels) == len(values):
        clean_labels = [lb for lb, v in zip(labels, values) if v is not None and _is_numeric(v)]
        if clean_labels:
            result["first_label"] = clean_labels[0]
            result["last_label"] = clean_labels[-1]
    return json.dumps(result, indent=2)


def _op_compare(values, **kw) -> str:
    b = kw.get("y") or []
    a_label = kw.get("a_label", "sample_a")
    b_label = kw.get("b_label", "sample_b")
    ca, cb = _clean(values), _clean(b)
    if len(ca) < 1:
        return json.dumps({"error": f"Need at least 1 numeric {a_label}."})
    if len(cb) < 1:
        return json.dumps({"error": f"Need at least 1 numeric {b_label}."})
    aa, ab = np.array(ca), np.array(cb)
    mean_a, mean_b = float(np.mean(aa)), float(np.mean(ab))
    std_a = float(np.std(aa, ddof=1)) if len(ca) > 1 else 0.0
    std_b = float(np.std(ab, ddof=1)) if len(cb) > 1 else 0.0
    diff = mean_b - mean_a
    pct = (diff / mean_a * 100) if mean_a != 0 else None
    pooled_std = np.sqrt(
        ((len(ca) - 1) * std_a ** 2 + (len(cb) - 1) * std_b ** 2)
        / max(len(ca) + len(cb) - 2, 1)
    )
    cohens_d = diff / pooled_std if pooled_std > 0 else 0.0
    abs_d = abs(cohens_d)
    effect = "large" if abs_d >= 0.8 else "medium" if abs_d >= 0.5 else "small" if abs_d >= 0.2 else "negligible"
    return json.dumps({
        a_label: {"count": len(ca), "mean": round(mean_a, 4), "median": round(float(np.median(aa)), 4), "std_dev": round(std_a, 4)},
        b_label: {"count": len(cb), "mean": round(mean_b, 4), "median": round(float(np.median(ab)), 4), "std_dev": round(std_b, 4)},
        "difference": round(diff, 4), "pct_change": round(pct, 2) if pct is not None else None,
        "higher": b_label if diff > 0 else a_label if diff < 0 else "equal",
        "cohens_d": round(cohens_d, 4), "effect_size": effect,
    }, indent=2)


def _op_moving_average(values, **kw) -> str:
    window = kw.get("window", 7)
    labels = kw.get("labels")
    clean = _clean(values)
    err = _require_min(clean, window, f"values for {window}-point moving average")
    if err:
        return err
    arr = np.array(clean)
    kernel = np.ones(window) / window
    sma = np.convolve(arr, kernel, mode="valid")
    sma_list = [round(float(v), 4) for v in sma]
    offset = window - 1
    points: list[dict[str, Any]] = []
    clean_labels = None
    if labels and len(labels) == len(values):
        clean_labels = [lb for lb, v in zip(labels, values) if v is not None and _is_numeric(v)]
    for i, val in enumerate(sma_list):
        pt: dict[str, Any] = {"index": i + offset, "sma": val}
        if clean_labels and (i + offset) < len(clean_labels):
            pt["label"] = clean_labels[i + offset]
        points.append(pt)
    if len(sma_list) >= 2:
        direction = "increasing" if sma_list[-1] > sma_list[0] else "decreasing" if sma_list[-1] < sma_list[0] else "stable"
    else:
        direction = "insufficient data"
    return json.dumps({
        "window": window, "input_count": len(clean), "output_count": len(sma_list),
        "direction": direction, "first_sma": sma_list[0], "last_sma": sma_list[-1], "points": points,
    }, indent=2)


def _op_outliers(values, **kw) -> str:
    method = kw.get("method", "iqr")
    threshold = kw.get("threshold", 1.5)
    clean = _clean(values)
    err = _require_min(clean, 4, "values for outlier detection")
    if err:
        return err
    arr = np.array(clean)
    if method.lower() == "zscore":
        mean = float(np.mean(arr))
        std = float(np.std(arr, ddof=1))
        if std == 0:
            return json.dumps({"outliers": [], "message": "Zero variance – no outliers."})
        z_scores = (arr - mean) / std
        mask = np.abs(z_scores) > threshold
        outlier_indices = np.where(mask)[0].tolist()
        result: dict[str, Any] = {
            "method": "zscore", "threshold": threshold,
            "mean": round(mean, 4), "std_dev": round(std, 4),
            "lower_bound": round(mean - threshold * std, 4),
            "upper_bound": round(mean + threshold * std, 4),
        }
    else:
        q1, q3 = float(np.percentile(arr, 25)), float(np.percentile(arr, 75))
        iqr = q3 - q1
        lower = q1 - threshold * iqr
        upper = q3 + threshold * iqr
        mask = (arr < lower) | (arr > upper)
        outlier_indices = np.where(mask)[0].tolist()
        result = {
            "method": "iqr", "multiplier": threshold,
            "q1": round(q1, 4), "q3": round(q3, 4), "iqr": round(iqr, 4),
            "lower_fence": round(lower, 4), "upper_fence": round(upper, 4),
        }
    original_indices = [i for i, v in enumerate(values) if v is not None and _is_numeric(v)]
    outliers = [
        {"index": original_indices[i], "value": round(clean[i], 4)}
        for i in outlier_indices
    ]
    result["outlier_count"] = len(outliers)
    result["sample_size"] = len(clean)
    result["outliers"] = outliers
    return json.dumps(result, indent=2)


_OPERATIONS = {
    "describe": _op_describe,
    "percentiles": _op_percentiles,
    "correlation": _op_correlation,
    "trend": _op_trend,
    "compare": _op_compare,
    "moving_average": _op_moving_average,
    "outliers": _op_outliers,
}


# ---------------------------------------------------------------------------
# Tool registration (single tool)
# ---------------------------------------------------------------------------

def register_stats_tools(mcp_instance) -> None:

    @mcp_instance.tool()
    def garmin_stats(
        operation: str,
        values: list[float | None],
        y: list[float | None] | None = None,
        labels: list[str] | None = None,
        method: str = "pearson",
        window: int = 7,
        threshold: float = 1.5,
        percentiles: list[float] | None = None,
        a_label: str = "sample_a",
        b_label: str = "sample_b",
    ) -> str:
        """
        Perform a statistical analysis operation on numeric data.

        operation: one of "describe", "percentiles", "correlation", "trend",
                   "compare", "moving_average", "outliers".

        Common params:
          values: primary list of numeric values (required for all operations).
          y: second list of values (for "correlation" and "compare").
          labels: parallel date/label list (for "trend" and "moving_average").

        Operation-specific params:
          describe: (no extra params needed)
          percentiles: percentiles (list of ranks 0-100, default [5,10,25,50,75,90,95])
          correlation: y (required), method ("pearson" or "spearman")
          trend: labels (optional date labels)
          compare: y (required sample B), a_label, b_label
          moving_average: window (default 7), labels
          outliers: method ("iqr" or "zscore"), threshold (default 1.5)

        Examples:
          Descriptive stats: operation="describe", values=[65,62,68,70,64]
          Trend analysis:    operation="trend", values=[rhr_vals...], labels=[dates...]
          Correlation:       operation="correlation", values=[steps...], y=[sleep_scores...], method="pearson"
          Compare weeks:     operation="compare", values=[this_week...], y=[last_week...], a_label="this_week", b_label="last_week"
        """
        op = operation.lower().strip()
        if op not in _OPERATIONS:
            return json.dumps({"error": f"Unknown operation '{operation}'. Use: {', '.join(_OPERATIONS)}"})

        kw = {
            "y": y, "labels": labels, "method": method, "window": window,
            "threshold": threshold, "percentiles": percentiles,
            "a_label": a_label, "b_label": b_label,
        }
        return _OPERATIONS[op](values, **kw)
