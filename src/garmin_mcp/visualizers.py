"""
Visualizer tool -- single matplotlib-based charting endpoint for Garmin metric data.

Accepts a chart_type and plottable data, renders the chart, saves it to disk,
and returns the image as a native MCP ImageContent block (rendered inline by
Claude Desktop) alongside a JSON text block with the file path.

Output directory: ``output/viz/`` or ``OUTPUT_DIR`` env var.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from fastmcp.utilities.types import Image as MCPImage


_OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join("output", "viz"))


def _save_fig(fig: plt.Figure, tag: str) -> str:
    """Save *fig* to PNG on disk and return the absolute file path."""
    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{tag}.png"
    filepath = os.path.join(_OUTPUT_DIR, filename)
    fig.savefig(filepath, format="png", bbox_inches="tight", dpi=150)
    plt.close(fig)
    return os.path.abspath(filepath)


def _apply_style(ax: plt.Axes, title: str | None, x_label: str | None, y_label: str | None) -> None:
    if title:
        ax.set_title(title, fontsize=13, fontweight="bold")
    if x_label:
        ax.set_xlabel(x_label)
    if y_label:
        ax.set_ylabel(y_label)
    ax.grid(True, alpha=0.3)


def _set_x_ticks(ax, x):
    if x:
        step = max(1, len(x) // 12)
        ax.set_xticks(range(0, len(x), step))
        ax.set_xticklabels([str(v) for v in x[::step]], rotation=45, ha="right")


# ---------------------------------------------------------------------------
# Chart renderers (internal)
# ---------------------------------------------------------------------------

def _render_line(ax, x, y, **_kw):
    y_clean = [v if v is not None else float("nan") for v in y]
    ax.plot(range(len(y_clean)), y_clean, marker="o", linewidth=2, markersize=4)
    _set_x_ticks(ax, x)


def _render_bar(ax, x, y, **_kw):
    labels = x or [str(i) for i in range(len(y))]
    colors = plt.cm.tab10(np.linspace(0, 1, len(labels)))
    ax.bar(range(len(labels)), y, color=colors)
    ax.set_xticks(range(len(labels)))
    ax.set_xticklabels(labels, rotation=45, ha="right")


def _render_scatter(ax, x, y, **_kw):
    ax.scatter(x, y, alpha=0.7, edgecolors="white", linewidth=0.5)
    if len(x) >= 3:
        z = np.polyfit(x, y, 1)
        p = np.poly1d(z)
        x_sorted = sorted(x)
        ax.plot(x_sorted, p(x_sorted), "--", color="red", alpha=0.6, label="trend")
        ax.legend()


def _render_histogram(ax, x, y, **kw):
    bins = kw.get("bins", 20)
    y_clean = [v for v in y if v is not None]
    ax.hist(y_clean, bins=bins, edgecolor="white", alpha=0.8)


def _render_pie(ax, x, y, **_kw):
    labels = x or [str(i) for i in range(len(y))]
    ax.pie(y, labels=labels[:len(y)], autopct="%1.1f%%", startangle=140, pctdistance=0.85)


def _render_heatmap(fig, ax, x, y, **kw):
    matrix = kw.get("matrix", [])
    if not matrix:
        raise ValueError("heatmap requires 'matrix' (a 2-D list of numbers)")
    arr = np.array(matrix, dtype=float)
    im = ax.imshow(arr, aspect="auto", cmap="YlOrRd")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    x_labels = kw.get("x_labels")
    y_labels = kw.get("y_labels")
    if x_labels:
        ax.set_xticks(range(len(x_labels)))
        ax.set_xticklabels(x_labels, rotation=45, ha="right")
    if y_labels:
        ax.set_yticks(range(len(y_labels)))
        ax.set_yticklabels(y_labels)


def _render_multi_line(ax, x, y, **kw):
    y_series = kw.get("y_series", [])
    if not y_series:
        raise ValueError("multi_line requires 'y_series' (list of y-value lists)")
    series_labels = kw.get("series_labels") or [f"Series {i+1}" for i in range(len(y_series))]
    for i, ys in enumerate(y_series):
        ys_clean = [v if v is not None else float("nan") for v in ys]
        ax.plot(range(len(ys_clean)), ys_clean, marker="o", linewidth=2, markersize=3, label=series_labels[i])
    _set_x_ticks(ax, x)
    ax.legend()


_RENDERERS = {
    "line": _render_line,
    "bar": _render_bar,
    "scatter": _render_scatter,
    "histogram": _render_histogram,
    "pie": _render_pie,
    "heatmap": _render_heatmap,
    "multi_line": _render_multi_line,
}


# ---------------------------------------------------------------------------
# Tool registration (single tool)
# ---------------------------------------------------------------------------

def register_viz_tools(mcp_instance) -> None:

    @mcp_instance.tool()
    def garmin_viz(
        chart_type: str,
        x: list[str | float] | None = None,
        y: list[float | None] | None = None,
        title: str = "",
        x_label: str = "",
        y_label: str = "",
        matrix: list[list[float | None]] | None = None,
        x_labels: list[str] | None = None,
        y_labels: list[str] | None = None,
        y_series: list[list[float | None]] | None = None,
        series_labels: list[str] | None = None,
        bins: int = 20,
    ) -> list:
        """
        Render a chart and return the image inline (displayed by Claude Desktop)
        plus the saved file path.

        chart_type: "line", "bar", "scatter", "histogram", "pie", "heatmap", or "multi_line".

        Common params (used by most types):
          x: x-axis values or labels.
          y: y-axis values (for histogram, pass the data here).
          title, x_label, y_label: chart labels.

        Type-specific params:
          histogram: bins (default 20).
          heatmap: matrix (2-D list), x_labels, y_labels.
          multi_line: y_series (list of y-value lists), series_labels.

        Examples:
          Line:     chart_type="line", x=["Mon","Tue",...], y=[8000,9200,...]
          Bar:      chart_type="bar", x=["running","strength"], y=[5,3]
          Scatter:  chart_type="scatter", x=[steps...], y=[sleep_scores...]
          Histogram: chart_type="histogram", y=[hrv_values...]
          Pie:      chart_type="pie", x=["running","cycling"], y=[120,80]
          Heatmap:  chart_type="heatmap", matrix=[[...],[...]], x_labels=["Mon",...], y_labels=["Wk1",...]
          Multi-line: chart_type="multi_line", x=[dates...], y_series=[[rhr...],[stress...]], series_labels=["RHR","Stress"]
        """
        ct = chart_type.lower().strip()
        if ct not in _RENDERERS:
            return json.dumps({"error": f"Unknown chart_type '{chart_type}'. Use: {', '.join(_RENDERERS)}"})

        x = x or []
        y = y or []
        kw: dict[str, Any] = {
            "matrix": matrix, "x_labels": x_labels, "y_labels": y_labels,
            "y_series": y_series, "series_labels": series_labels, "bins": bins,
        }

        try:
            fig, ax = plt.subplots(figsize=(10, 6))
            renderer = _RENDERERS[ct]
            if ct == "heatmap":
                renderer(fig, ax, x, y, **kw)
            else:
                renderer(ax, x, y, **kw)
            if ct != "pie":
                _apply_style(ax, title, x_label, y_label)
            elif title:
                ax.set_title(title, fontsize=13, fontweight="bold")
            filepath = _save_fig(fig, ct)
        except Exception as exc:
            return json.dumps({"error": str(exc)})

        return [
            json.dumps({"chart_type": ct, "file_path": filepath}),
            MCPImage(path=filepath),
        ]
