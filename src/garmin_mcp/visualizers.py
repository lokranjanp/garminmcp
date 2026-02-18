"""
Visualizer tools -- lightweight matplotlib-based charting for Garmin metric data.

Each tool accepts plottable data directly, renders a chart, saves it to disk,
and returns both the file path and a base64-encoded PNG in the JSON response.

Output directory: ``output/viz/`` (auto-created).
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
from typing import Any

import matplotlib
matplotlib.use("Agg")  # headless backend -- no GUI required
import matplotlib.pyplot as plt
import numpy as np


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

_OUTPUT_DIR = os.path.join("output", "viz")


def _save_and_encode(fig: plt.Figure, tag: str) -> dict[str, str]:
    """Save *fig* to PNG and return ``{"file_path": ..., "base64_png": ...}``."""
    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{tag}.png"
    filepath = os.path.join(_OUTPUT_DIR, filename)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    fig.savefig(filepath, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)

    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode("ascii")
    return {"file_path": os.path.abspath(filepath), "base64_png": b64}


def _apply_style(ax: plt.Axes, title: str | None, x_label: str | None, y_label: str | None) -> None:
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold")
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.3)


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_viz_tools(mcp_instance) -> None:
    """Register lightweight matplotlib visualization tools on the MCP instance."""

    # ── 1. Line chart ──────────────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_viz_line(
        x: list[str | float],
        y: list[float],
        title: str = "Line Chart",
        x_label: str = "",
        y_label: str = "",
    ) -> str:
        """
        Render a line chart. x: category labels or numeric x-axis values,
        y: numeric y-axis values.  Returns file_path + base64 PNG.

        Example: plot daily step counts (x=dates, y=steps).
        """
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.plot(range(len(y)), y, marker="o", linewidth=2, markersize=4)
        if x:
            step = max(1, len(x) // 12)
            ax.set_xticks(range(0, len(x), step))
            ax.set_xticklabels([str(v) for v in x[::step]], rotation=45, ha="right")
        _apply_style(ax, title, x_label, y_label)
        result = _save_and_encode(fig, "line")
        return json.dumps(result, indent=2)

    # ── 2. Bar chart ───────────────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_viz_bar(
        labels: list[str],
        values: list[float],
        title: str = "Bar Chart",
        x_label: str = "",
        y_label: str = "",
    ) -> str:
        """
        Render a vertical bar chart.  labels: category names, values: bar heights.
        Returns file_path + base64 PNG.

        Example: activity type breakdown (labels=types, values=counts).
        """
        fig, ax = plt.subplots(figsize=(10, 5))
        colors = plt.cm.tab10(np.linspace(0, 1, len(labels)))
        ax.bar(range(len(labels)), values, color=colors)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        _apply_style(ax, title, x_label, y_label)
        result = _save_and_encode(fig, "bar")
        return json.dumps(result, indent=2)

    # ── 3. Scatter plot ────────────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_viz_scatter(
        x: list[float],
        y: list[float],
        title: str = "Scatter Plot",
        x_label: str = "",
        y_label: str = "",
    ) -> str:
        """
        Render a scatter plot of two numeric variables.
        Returns file_path + base64 PNG.

        Example: correlate daily steps (x) with sleep score (y).
        """
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.scatter(x, y, alpha=0.7, edgecolors="white", linewidth=0.5)
        # trend line
        if len(x) >= 3:
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            x_sorted = sorted(x)
            ax.plot(x_sorted, p(x_sorted), "--", color="red", alpha=0.6, label="trend")
            ax.legend()
        _apply_style(ax, title, x_label, y_label)
        result = _save_and_encode(fig, "scatter")
        return json.dumps(result, indent=2)

    # ── 4. Histogram ───────────────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_viz_histogram(
        values: list[float],
        bins: int = 20,
        title: str = "Histogram",
        x_label: str = "",
    ) -> str:
        """
        Render a histogram (frequency distribution).
        Returns file_path + base64 PNG.

        Example: distribution of nightly HRV values.
        """
        fig, ax = plt.subplots(figsize=(9, 5))
        ax.hist(values, bins=bins, edgecolor="white", alpha=0.8)
        _apply_style(ax, title, x_label, "Frequency")
        result = _save_and_encode(fig, "histogram")
        return json.dumps(result, indent=2)

    # ── 5. Pie chart ───────────────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_viz_pie(
        labels: list[str],
        values: list[float],
        title: str = "Pie Chart",
    ) -> str:
        """
        Render a pie chart.  labels: slice names, values: slice sizes.
        Returns file_path + base64 PNG.

        Example: activity type distribution by duration.
        """
        fig, ax = plt.subplots(figsize=(7, 7))
        ax.pie(
            values,
            labels=labels,
            autopct="%1.1f%%",
            startangle=140,
            pctdistance=0.85,
        )
        if title:
            ax.set_title(title, fontsize=13, fontweight="bold")
        result = _save_and_encode(fig, "pie")
        return json.dumps(result, indent=2)

    # ── 6. Heatmap ─────────────────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_viz_heatmap(
        matrix: list[list[float]],
        x_labels: list[str] | None = None,
        y_labels: list[str] | None = None,
        title: str = "Heatmap",
    ) -> str:
        """
        Render a heatmap from a 2-D matrix.
        x_labels: column headers, y_labels: row headers.
        Returns file_path + base64 PNG.

        Example: weekly stress levels (rows=weeks, cols=days).
        """
        arr = np.array(matrix, dtype=float)
        fig, ax = plt.subplots(figsize=(max(6, arr.shape[1] * 0.9), max(4, arr.shape[0] * 0.7)))
        im = ax.imshow(arr, aspect="auto", cmap="YlOrRd")
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
        if x_labels:
            ax.set_xticks(range(len(x_labels)))
            ax.set_xticklabels(x_labels, rotation=45, ha="right")
        if y_labels:
            ax.set_yticks(range(len(y_labels)))
            ax.set_yticklabels(y_labels)
        if title:
            ax.set_title(title, fontsize=13, fontweight="bold")
        result = _save_and_encode(fig, "heatmap")
        return json.dumps(result, indent=2)

    # ── 7. Multi-line chart ────────────────────────────────────────────

    @mcp_instance.tool()
    def garmin_viz_multi_line(
        x: list[str | float],
        y_series: list[list[float]],
        series_labels: list[str] | None = None,
        title: str = "Multi-Line Chart",
        x_label: str = "",
        y_label: str = "",
    ) -> str:
        """
        Overlay multiple line series on one chart.
        x: shared x-axis values, y_series: list of y-value lists (one per line),
        series_labels: legend names for each series.
        Returns file_path + base64 PNG.

        Example: compare RHR, sleep score, and stress over the same date range.
        """
        fig, ax = plt.subplots(figsize=(10, 5))
        labels = series_labels or [f"Series {i+1}" for i in range(len(y_series))]
        for i, ys in enumerate(y_series):
            ax.plot(range(len(ys)), ys, marker="o", linewidth=2, markersize=3, label=labels[i])
        if x:
            step = max(1, len(x) // 12)
            ax.set_xticks(range(0, len(x), step))
            ax.set_xticklabels([str(v) for v in x[::step]], rotation=45, ha="right")
        ax.legend()
        _apply_style(ax, title, x_label, y_label)
        result = _save_and_encode(fig, "multi_line")
        return json.dumps(result, indent=2)
