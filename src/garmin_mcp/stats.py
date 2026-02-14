"""
Stats tools – statistical analysis helpers for Garmin metric samples.

These tools accept raw numeric arrays (as returned by other Garmin tools) and
perform common statistical operations.  They are registered as MCP tools so an
AI client can pipe metric data through them without leaving the MCP context.

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
    """Strip None/non-numeric entries and return a list of floats."""
    out: list[float] = []
    for v in values:
        if v is None:
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def _require_min(clean: list[float], n: int, label: str = "values") -> str | None:
    """Return an error JSON string if len(clean) < n, else None."""
    if len(clean) < n:
        return json.dumps({
            "error": f"Need at least {n} numeric {label}, got {len(clean)}."
        })
    return None


def _safe_mode(vals: list[float]) -> float | str:
    """Return mode; if no unique mode, return 'no unique mode'."""
    try:
        return statistics.mode(vals)
    except statistics.StatisticsError:
        return "no unique mode"


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_stats_tools(mcp_instance) -> None:
    """Register statistical-analysis tools on the given FastMCP instance."""

    # ── 1. Descriptive statistics ──────────────────────────────────────

    @mcp_instance.tool()
    def garmin_stats_describe(values: list[float | None]) -> str:
        """
        Compute descriptive statistics for a list of numeric values.

        Returns: count, mean, median, mode, std_dev, variance, min, max,
        range, Q1 (25th pctl), Q3 (75th pctl), IQR, skewness, kurtosis.

        Pass any numeric sample – e.g. a week of daily step counts, HRV
        readings, sleep scores, resting heart rates, etc.
        """
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

        # Skewness & kurtosis (need >= 3 values for meaningful result)
        if n >= 3:
            mean = np.mean(arr)
            std = np.std(arr, ddof=1)
            if std > 0:
                skew = float(np.mean(((arr - mean) / std) ** 3))
                kurt = float(np.mean(((arr - mean) / std) ** 4) - 3)  # excess kurtosis
                result["skewness"] = round(skew, 4)
                result["kurtosis"] = round(kurt, 4)

        return json.dumps(result, indent=2)

    # ── 2. Percentiles ─────────────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_stats_percentiles(
        values: list[float | None],
        percentiles: list[float] | None = None,
    ) -> str:
        """
        Compute specific percentiles for a list of numeric values.

        percentiles: list of percentile ranks (0-100).
        Defaults to [5, 10, 25, 50, 75, 90, 95] if omitted.
        """
        clean = _clean(values)
        err = _require_min(clean, 1)
        if err:
            return err

        ptiles = percentiles or [5, 10, 25, 50, 75, 90, 95]
        arr = np.array(clean)
        result = {
            f"p{int(p) if p == int(p) else p}": round(float(np.percentile(arr, p)), 4)
            for p in ptiles
        }
        result["count"] = len(clean)
        return json.dumps(result, indent=2)

    # ── 3. Correlation ─────────────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_stats_correlation(
        x: list[float | None],
        y: list[float | None],
        method: str = "pearson",
    ) -> str:
        """
        Compute correlation between two equal-length numeric samples.

        method: "pearson" (linear) or "spearman" (rank-based).
        Returns: coefficient (r), r_squared, interpretation, and sample size.

        Example: correlate daily steps with sleep scores to see if they relate.
        """
        cx, cy = _clean(x), _clean(y)
        # Pair-wise: only keep indices where both are present
        pairs = [
            (float(a), float(b))
            for a, b in zip(x, y)
            if a is not None and b is not None
            and _is_numeric(a) and _is_numeric(b)
        ]
        if len(pairs) < 3:
            return json.dumps({
                "error": "Need at least 3 paired numeric values for correlation."
            })

        ax = np.array([p[0] for p in pairs])
        ay = np.array([p[1] for p in pairs])

        if method.lower() == "spearman":
            # Rank-based
            ax_ranks = np.argsort(np.argsort(ax)).astype(float)
            ay_ranks = np.argsort(np.argsort(ay)).astype(float)
            r = float(np.corrcoef(ax_ranks, ay_ranks)[0, 1])
        else:
            r = float(np.corrcoef(ax, ay)[0, 1])

        abs_r = abs(r)
        if abs_r >= 0.8:
            strength = "strong"
        elif abs_r >= 0.5:
            strength = "moderate"
        elif abs_r >= 0.3:
            strength = "weak"
        else:
            strength = "negligible"

        direction = "positive" if r > 0 else "negative" if r < 0 else "none"

        return json.dumps({
            "method": method.lower(),
            "r": round(r, 6),
            "r_squared": round(r ** 2, 6),
            "strength": strength,
            "direction": direction,
            "interpretation": f"{strength} {direction} correlation",
            "sample_size": len(pairs),
        }, indent=2)

    # ── 4. Trend / linear regression ───────────────────────────────────

    @mcp_instance.tool()
    def garmin_stats_trend(
        values: list[float | None],
        labels: list[str] | None = None,
    ) -> str:
        """
        Fit a linear trend to an ordered sequence of numeric values.

        values: ordered samples (e.g. daily RHR over 14 days, oldest first).
        labels: optional parallel list of labels (e.g. dates) for context.

        Returns: slope (change per unit/day), intercept, r_squared, direction
        ("improving" / "declining" / "stable"), predicted next value.
        """
        clean = _clean(values)
        err = _require_min(clean, 3, "values for trend")
        if err:
            return err

        arr = np.array(clean)
        x = np.arange(len(arr), dtype=float)

        # Linear regression: y = slope * x + intercept
        coeffs = np.polyfit(x, arr, 1)
        slope, intercept = float(coeffs[0]), float(coeffs[1])

        # R-squared
        predicted = np.polyval(coeffs, x)
        ss_res = float(np.sum((arr - predicted) ** 2))
        ss_tot = float(np.sum((arr - np.mean(arr)) ** 2))
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Direction (threshold: slope must explain > 10% of variance to be meaningful)
        if r_squared < 0.1:
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"

        next_val = float(np.polyval(coeffs, len(arr)))

        result: dict[str, Any] = {
            "slope_per_unit": round(slope, 6),
            "intercept": round(intercept, 4),
            "r_squared": round(r_squared, 6),
            "direction": direction,
            "predicted_next": round(next_val, 4),
            "sample_size": len(clean),
            "first_value": clean[0],
            "last_value": clean[-1],
            "total_change": round(clean[-1] - clean[0], 4),
            "pct_change": round(((clean[-1] - clean[0]) / clean[0]) * 100, 2) if clean[0] != 0 else None,
        }

        if labels and len(labels) == len(values):
            # Map labels to non-None values
            clean_labels = [l for l, v in zip(labels, values) if v is not None and _is_numeric(v)]
            if clean_labels:
                result["first_label"] = clean_labels[0]
                result["last_label"] = clean_labels[-1]

        return json.dumps(result, indent=2)

    # ── 5. Compare two samples ─────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_stats_compare(
        a: list[float | None],
        b: list[float | None],
        a_label: str = "sample_a",
        b_label: str = "sample_b",
    ) -> str:
        """
        Compare two numeric samples (e.g. this week's vs last week's step counts).

        Returns: per-sample stats (mean, median, std_dev), difference, percent
        change, Cohen's d effect size, and which sample is higher.
        """
        ca, cb = _clean(a), _clean(b)
        err_a = _require_min(ca, 1, a_label)
        err_b = _require_min(cb, 1, b_label)
        if err_a:
            return err_a
        if err_b:
            return err_b

        aa, ab = np.array(ca), np.array(cb)
        mean_a, mean_b = float(np.mean(aa)), float(np.mean(ab))
        std_a, std_b = (
            float(np.std(aa, ddof=1)) if len(ca) > 1 else 0.0,
            float(np.std(ab, ddof=1)) if len(cb) > 1 else 0.0,
        )
        diff = mean_b - mean_a
        pct = (diff / mean_a * 100) if mean_a != 0 else None

        # Cohen's d (pooled std)
        pooled_std = np.sqrt(
            ((len(ca) - 1) * std_a ** 2 + (len(cb) - 1) * std_b ** 2)
            / max(len(ca) + len(cb) - 2, 1)
        )
        cohens_d = diff / pooled_std if pooled_std > 0 else 0.0

        abs_d = abs(cohens_d)
        if abs_d >= 0.8:
            effect = "large"
        elif abs_d >= 0.5:
            effect = "medium"
        elif abs_d >= 0.2:
            effect = "small"
        else:
            effect = "negligible"

        return json.dumps({
            a_label: {
                "count": len(ca),
                "mean": round(mean_a, 4),
                "median": round(float(np.median(aa)), 4),
                "std_dev": round(std_a, 4),
            },
            b_label: {
                "count": len(cb),
                "mean": round(mean_b, 4),
                "median": round(float(np.median(ab)), 4),
                "std_dev": round(std_b, 4),
            },
            "difference": round(diff, 4),
            "pct_change": round(pct, 2) if pct is not None else None,
            "higher": b_label if diff > 0 else a_label if diff < 0 else "equal",
            "cohens_d": round(cohens_d, 4),
            "effect_size": effect,
        }, indent=2)

    # ── 6. Moving average ──────────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_stats_moving_average(
        values: list[float | None],
        window: int = 7,
        labels: list[str] | None = None,
    ) -> str:
        """
        Compute a simple moving average (SMA) over an ordered list of values.

        window: number of points to average (default 7 for a weekly window).
        labels: optional parallel list of labels (e.g. dates).

        Returns the smoothed series (shorter by window-1) and the overall
        smoothed trend direction.
        """
        clean = _clean(values)
        err = _require_min(clean, window, f"values for {window}-point moving average")
        if err:
            return err

        arr = np.array(clean)
        kernel = np.ones(window) / window
        sma = np.convolve(arr, kernel, mode="valid")
        sma_list = [round(float(v), 4) for v in sma]

        # Build output points
        offset = window - 1
        points: list[dict[str, Any]] = []
        clean_labels = None
        if labels and len(labels) == len(values):
            clean_labels = [l for l, v in zip(labels, values) if v is not None and _is_numeric(v)]

        for i, val in enumerate(sma_list):
            pt: dict[str, Any] = {"index": i + offset, "sma": val}
            if clean_labels and (i + offset) < len(clean_labels):
                pt["label"] = clean_labels[i + offset]
            points.append(pt)

        # Direction of the SMA itself
        if len(sma_list) >= 2:
            if sma_list[-1] > sma_list[0]:
                direction = "increasing"
            elif sma_list[-1] < sma_list[0]:
                direction = "decreasing"
            else:
                direction = "stable"
        else:
            direction = "insufficient data"

        return json.dumps({
            "window": window,
            "input_count": len(clean),
            "output_count": len(sma_list),
            "direction": direction,
            "first_sma": sma_list[0],
            "last_sma": sma_list[-1],
            "points": points,
        }, indent=2)

    # ── 7. Outlier detection ───────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_stats_outliers(
        values: list[float | None],
        method: str = "iqr",
        threshold: float = 1.5,
    ) -> str:
        """
        Detect outliers in a numeric sample.

        method: "iqr" (Tukey's fences, default) or "zscore".
        threshold: IQR multiplier (default 1.5) or z-score cutoff (default 1.5; typical: 2 or 3).

        Returns the outlier values, their indices, and the fence/threshold boundaries.
        """
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
            result = {
                "method": "zscore",
                "threshold": threshold,
                "mean": round(mean, 4),
                "std_dev": round(std, 4),
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
                "method": "iqr",
                "multiplier": threshold,
                "q1": round(q1, 4),
                "q3": round(q3, 4),
                "iqr": round(iqr, 4),
                "lower_fence": round(lower, 4),
                "upper_fence": round(upper, 4),
            }

        # Map outlier indices back to original (pre-clean) indices
        original_indices = [i for i, v in enumerate(values) if v is not None and _is_numeric(v)]
        outliers = [
            {
                "index": original_indices[i],
                "value": round(clean[i], 4),
            }
            for i in outlier_indices
        ]
        result["outlier_count"] = len(outliers)
        result["sample_size"] = len(clean)
        result["outliers"] = outliers

        return json.dumps(result, indent=2)


# ---------------------------------------------------------------------------
# Utility used across tools
# ---------------------------------------------------------------------------

def _is_numeric(v: Any) -> bool:
    """Check if a value is numeric (int/float)."""
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return True
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False
