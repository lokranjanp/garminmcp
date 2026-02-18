"""
LIDA-based visualization tools -- AI-driven chart generation via Microsoft LIDA.

LIDA auto-determines the best chart type given data and an optional natural-
language goal.  It supports any grammar (matplotlib, seaborn, plotly, etc.)
and works with OpenAI, LM Studio, or any OpenAI-compatible LLM endpoint.

LLM configuration is read from environment variables:

    LLM_PROVIDER   – "openai" (default) or "hf"
    LLM_API_BASE   – custom endpoint (e.g. http://localhost:1234/v1 for LM Studio)
    LLM_API_KEY    – API key (use "lm-studio" for LM Studio)
    LLM_MODEL      – model name (default: gpt-4o-mini)
"""

from __future__ import annotations

import base64
import csv
import json
import os
import tempfile
import time
from typing import Any

from mcp.types import ImageContent, TextContent


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

_OUTPUT_DIR = os.environ.get("OUTPUT_DIR", os.path.join("output", "viz"))


def _save_chart_b64(raster_b64: str, tag: str) -> str:
    """Persist a base64 PNG to disk and return the absolute file path."""
    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    ts = time.strftime("%Y%m%d_%H%M%S")
    filename = f"{ts}_{tag}.png"
    filepath = os.path.join(_OUTPUT_DIR, filename)

    raw = base64.b64decode(raster_b64)
    with open(filepath, "wb") as f:
        f.write(raw)

    return os.path.abspath(filepath)


# ---------------------------------------------------------------------------
# LLM / LIDA helpers
# ---------------------------------------------------------------------------

def _get_lida_manager():
    """
    Build and return a ``lida.Manager`` configured from env vars.

    Supports:
      - OpenAI (default):  set LLM_API_KEY
      - LM Studio:         set LLM_API_BASE=http://localhost:1234/v1,
                            LLM_API_KEY=lm-studio, LLM_MODEL=<model>
      - Any OpenAI-compatible endpoint: same as LM Studio pattern
    """
    from lida import Manager, llm

    provider = os.environ.get("LLM_PROVIDER", "openai").strip()
    api_base = os.environ.get("LLM_API_BASE", "").strip() or None
    api_key = os.environ.get("LLM_API_KEY", "").strip() or None
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini").strip()

    kwargs: dict[str, Any] = {}
    if api_base:
        kwargs["api_base"] = api_base
    if api_key:
        kwargs["api_key"] = api_key

    if api_base:
        model_details = [{
            "name": model,
            "max_tokens": 4096,
            "model": {"provider": "openai", "parameters": {"model": model}},
        }]
        text_gen = llm(provider="openai", models=model_details, **kwargs)
    else:
        text_gen = llm(provider=provider, **kwargs)

    return Manager(text_gen=text_gen)


def _data_to_csv_path(data: Any) -> str:
    """
    Convert ``data`` (list of dicts, dict of lists, or 2-D list) into a
    temporary CSV file and return its path.  LIDA requires a file path.
    """
    fd, path = tempfile.mkstemp(suffix=".csv", prefix="garmin_lida_")

    if isinstance(data, list) and data and isinstance(data[0], dict):
        keys = list(data[0].keys())
        with os.fdopen(fd, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
        return path

    if isinstance(data, dict):
        keys = list(data.keys())
        rows = zip(*(data[k] for k in keys))
        with os.fdopen(fd, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(keys)
            writer.writerows(rows)
        return path

    if isinstance(data, list) and data and isinstance(data[0], (list, tuple)):
        with os.fdopen(fd, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(data)
        return path

    os.close(fd)
    raise ValueError(
        "data must be a list of dicts, a dict of lists, or a 2-D list "
        "(first row = headers)."
    )


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

def register_lida_tools(mcp_instance) -> None:
    """Register LIDA-powered visualization tools on the MCP instance."""

    @mcp_instance.tool()
    def garmin_lida_visualize(
        data: list[dict] | dict[str, list] | list[list],
        goal: str = "",
        library: str = "matplotlib",
    ) -> list:
        """
        Generate a visualization using LIDA (AI-driven). Returns the chart
        as a native MCP image (rendered inline by Claude Desktop) plus metadata.

        data: plottable dataset in one of these shapes:
          - list of dicts:  [{"date":"2026-02-01","steps":8000}, ...]
          - dict of lists:  {"date":[...], "steps":[...]}
          - 2-D list:       [["date","steps"], ["2026-02-01",8000], ...]
        goal: natural-language visualization goal (e.g. "show trend of steps
              over time").  If empty, LIDA picks the best goal automatically.
        library: plotting library -- "matplotlib" (default), "seaborn", "plotly".

        Requires LLM env vars: LLM_API_KEY (and optionally LLM_API_BASE,
        LLM_MODEL for LM Studio / local LLMs).
        """
        try:
            manager = _get_lida_manager()
        except Exception as exc:
            return json.dumps({
                "error": f"Failed to initialize LIDA: {exc}",
                "hint": "Set LLM_API_KEY (and optionally LLM_API_BASE / LLM_MODEL) in env.",
            })

        try:
            csv_path = _data_to_csv_path(data)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})

        try:
            summary = manager.summarize(csv_path)

            if not goal:
                goals = manager.goals(summary, n=1)
                if goals:
                    goal = goals[0].question
                else:
                    goal = "Create an informative visualization of this data"

            charts = manager.visualize(
                summary=summary,
                goal=goal,
                library=library,
            )
        except Exception as exc:
            return json.dumps({"error": f"LIDA visualization failed: {exc}"})
        finally:
            try:
                os.unlink(csv_path)
            except OSError:
                pass

        if not charts:
            return json.dumps({"error": "LIDA returned no charts for this data/goal."})

        chart = charts[0]
        raster_b64 = chart.raster
        if not raster_b64:
            return json.dumps({
                "error": "Chart generated but no raster image produced.",
                "code": chart.code,
            })

        filepath = _save_chart_b64(raster_b64, "lida")
        meta = {
            "file_path": filepath,
            "goal": goal,
            "code": chart.code,
            "library": library,
        }
        return [
            TextContent(type="text", text=json.dumps(meta, indent=2)),
            ImageContent(type="image", data=raster_b64, mimeType="image/png"),
        ]

    @mcp_instance.tool()
    def garmin_lida_goals(
        data: list[dict] | dict[str, list] | list[list],
        n: int = 5,
    ) -> str:
        """
        Given a dataset, use LIDA to suggest N visualization goals (exploratory
        data analysis ideas).

        data: same shapes as garmin_lida_visualize.
        n: number of goals to generate (default 5).

        Returns a list of goal objects with question and rationale.
        """
        try:
            manager = _get_lida_manager()
        except Exception as exc:
            return json.dumps({
                "error": f"Failed to initialize LIDA: {exc}",
                "hint": "Set LLM_API_KEY env var.",
            })

        try:
            csv_path = _data_to_csv_path(data)
        except ValueError as exc:
            return json.dumps({"error": str(exc)})

        try:
            summary = manager.summarize(csv_path)
            goals = manager.goals(summary, n=n)
        except Exception as exc:
            return json.dumps({"error": f"LIDA goal generation failed: {exc}"})
        finally:
            try:
                os.unlink(csv_path)
            except OSError:
                pass

        result = []
        for g in goals:
            result.append({
                "index": g.index,
                "question": g.question,
                "visualization": g.visualization,
                "rationale": g.rationale,
            })

        return json.dumps({"goals": result, "count": len(result)}, indent=2)

    @mcp_instance.tool()
    def garmin_lida_explain(
        code: str,
        data: list[dict] | dict[str, list] | list[list] | None = None,
    ) -> str:
        """
        Explain a visualization's code in natural language using LIDA.

        code: the Python visualization code to explain.
        data: optional dataset (same shapes) to provide context for the explanation.

        Returns a structured explanation covering accessibility, data
        transformations, and chart semantics.
        """
        try:
            manager = _get_lida_manager()
        except Exception as exc:
            return json.dumps({
                "error": f"Failed to initialize LIDA: {exc}",
                "hint": "Set LLM_API_KEY env var.",
            })

        summary = None
        csv_path = None
        if data is not None:
            try:
                csv_path = _data_to_csv_path(data)
                summary = manager.summarize(csv_path)
            except Exception:
                pass

        try:
            explanation = manager.explain(code=code, summary=summary)
        except Exception as exc:
            return json.dumps({"error": f"LIDA explain failed: {exc}"})
        finally:
            if csv_path:
                try:
                    os.unlink(csv_path)
                except OSError:
                    pass

        if not explanation:
            return json.dumps({"explanation": "No explanation generated."})

        if isinstance(explanation, list):
            sections = []
            for item in explanation:
                if isinstance(item, dict):
                    sections.append(item)
                else:
                    sections.append({"content": str(item)})
            return json.dumps({"explanation": sections}, indent=2)

        return json.dumps({"explanation": str(explanation)}, indent=2)
