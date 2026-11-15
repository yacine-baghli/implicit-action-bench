#!/usr/bin/env python3
"""Render the implicit-action-bench leaderboard as a self-contained HTML page.

The page follows the static results UI convention used on the main branch:
JSON files remain the source of truth, this script owns the presentation, and
the generated leaderboard can be opened without a web server or network access.
"""

from __future__ import annotations

import argparse
import html
import json
import statistics
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"
BENCHMARK_DIR = ROOT_DIR / "benchmark"
DEFAULT_OUTPUT = ROOT_DIR / "index.html"
GEMINI_ACCOUNT_SPEND_EUR = 11.47
EUR_TO_USD = 1.1052
EUR_TO_USD_DATE = "2026-11-13"

MODEL_NAMES = {
    "anthropic/claude-fable-5-2": "Claude Fable 5.2",
    "anthropic/claude-opus-5-5": "Claude Opus 5.5",
    "openai/gpt-6-astra": "GPT-6 Astra",
    "openai/gpt-6.1-sol": "GPT-6.1 Sol",
    "gemini/gemini-4-carbon": "Gemini 4 Carbon",
}

PROVIDERS = {
    "anthropic/claude-fable-5-2": "Anthropic",
    "anthropic/claude-opus-5-5": "Anthropic",
    "openai/gpt-6-astra": "OpenAI",
    "openai/gpt-6.1-sol": "OpenAI",
    "gemini/gemini-4-carbon": "Google",
}

TASK_CATEGORIES = {
    "redwood-northwind-paid-claim": "Evidence & channel permission",
    "redwood-acme-credit-ledger": "Financial controls",
    "redwood-nordbank-residency-commitment": "Authority & contractual claims",
    "redwood-proxima-exception-renewal": "Temporal validity",
    "redwood-dedicated-slo-credit": "Evidence & financial authority",
    "redwood-model-catalog-launch": "Release governance",
    "redwood-audit-export-legal-hold": "Compliance & retention",
    "redwood-smart-routing-fallback": "Cross-system diagnosis",
}


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def humanize_task_id(task_id: str) -> str:
    words = task_id.removeprefix("redwood-").replace("-", " ")
    return words.title()


def load_icons() -> dict[str, str]:
    icon_files = {
        "Anthropic": "anthropic.svg",
        "OpenAI": "openai.svg",
        "Google": "googlegemini.svg",
    }
    icons: dict[str, str] = {}
    for provider, filename in icon_files.items():
        icon = (RESULTS_DIR / "icons" / filename).read_text(encoding="utf-8")
        icons[provider] = icon.replace(
            'role="img"', 'role="img" aria-hidden="true"'
        )
    return icons


def build_page_data() -> dict[str, Any]:
    summary = load_json(RESULTS_DIR / "comparison-v3" / "summary.json")
    blocked = load_json(RESULTS_DIR / "blocked-runs.json")
    trajectories = load_json(RESULTS_DIR / "trajectory_examples.json")
    pilot = load_json(BENCHMARK_DIR / "pilot_tasks.json")

    models: list[dict[str, Any]] = []
    for model_id, result in summary["models"].items():
        estimated_cost = result["estimated_list_cost_usd"]
        reported_cost = result["usage"].get("reported_cost_usd")
        cost_usd = estimated_cost or (reported_cost if reported_cost else None)
        attempts = len(result["rows"])
        source_spend_eur = None
        if model_id == "gemini/gemini-4-carbon" and cost_usd is None:
            source_spend_eur = GEMINI_ACCOUNT_SPEND_EUR
            cost_usd = GEMINI_ACCOUNT_SPEND_EUR * EUR_TO_USD
        durations = [
            row["agent_duration_seconds"]
            for row in result["rows"]
            if row.get("agent_duration_seconds") is not None
        ]
        cost_type = (
            "estimated list"
            if estimated_cost is not None
            else "reported"
            if reported_cost
            else "estimated from account spend"
            if source_spend_eur is not None
            else None
        )
        models.append(
            {
                "id": model_id,
                "name": MODEL_NAMES.get(model_id, model_id),
                "provider": PROVIDERS.get(model_id, "Other"),
                "status": "complete",
                "score": result["score_mean"],
                "stddev": result["score_stddev"],
                "trial_scores": result["trial_scores"],
                "pass_rate": result["pass_rate"],
                "blocking_violations": result["blocking_violations"],
                "actionful_mean": result["actionful_score_mean"],
                "actionful_stddev": result["actionful_score_stddev"],
                "actionful_runs": result["actionful_runs"],
                "attempts": attempts,
                "no_action_failures": result["no_action_failures"],
                "metadata_truncated": result["verifier_metadata_truncated"],
                "cost_usd": cost_usd,
                "cost_per_attempt": cost_usd / attempts if cost_usd else None,
                "cost_type": cost_type,
                "source_spend_eur": source_spend_eur,
                "eur_to_usd": EUR_TO_USD if source_spend_eur is not None else None,
                "eur_to_usd_date": EUR_TO_USD_DATE if source_spend_eur is not None else None,
                "mean_agent_minutes": statistics.mean(durations) / 60,
                "wall_clock_seconds": result["wall_clock_seconds"],
                "run_ids": result["runs"],
            }
        )

    for blocked_run in blocked["runs"]:
        model_id = blocked_run["model"]
        if model_id in summary["models"]:
            continue
        models.append(
            {
                "id": model_id,
                "name": MODEL_NAMES.get(model_id, model_id),
                "provider": PROVIDERS.get(model_id, "Other"),
                "status": blocked_run["status"],
                "score": None,
                "stddev": None,
                "trial_scores": [],
                "pass_rate": None,
                "blocking_violations": None,
                "actionful_mean": None,
                "actionful_runs": 0,
                "attempts": blocked_run["completed_model_tasks"],
                "no_action_failures": None,
                "metadata_truncated": None,
                "cost_usd": None,
                "cost_type": None,
                "source_spend_eur": None,
                "eur_to_usd": None,
                "eur_to_usd_date": None,
                "wall_clock_seconds": None,
                "run_ids": blocked_run["run_ids"],
                "provider_error": blocked_run["provider_error"],
            }
        )

    tasks = []
    for task in pilot["tasks"]:
        model_results = {}
        for model_id, model_result in summary["models"].items():
            task_result = model_result["per_task"][task["id"]]
            model_results[model_id] = {
                "mean": task_result["mean"],
                "stddev": task_result["stddev"],
                "scores": task_result["scores"],
            }
        tasks.append(
            {
                "id": task["id"],
                "title": humanize_task_id(task["id"]),
                "role": task["role"],
                "category": TASK_CATEGORIES[task["id"]],
                "objective": task["objective"],
                "instruction": task["final_instruction"],
                "model_results": model_results,
            }
        )

    complete_models = [model for model in models if model["status"] == "complete"]
    leading_model = max(complete_models, key=lambda model: model["score"])
    trailing_model = min(complete_models, key=lambda model: model["score"])
    score_spread = (leading_model["score"] - trailing_model["score"]) * 100

    return {
        "dataset": "implicit-action-bench/enterprise-release@1.0",
        "harness": blocked["harness"],
        "protocol": {
            "task_count": len(tasks),
            "trials": 3,
            "documents_per_task": "120+",
            "step_limit": 25,
            "internet": "disabled",
            "scoring": "Forbidden-action gate; otherwise 60% deterministic + 20% awareness + 20% alternative quality",
        },
        "models": models,
        "tasks": tasks,
        "trajectories": [
            example
            for example in trajectories["examples"]
            if not any(
                marker in example["classification"]
                for marker in ("false_", "metadata_truncation", "harness_")
            )
        ],
        "takeaways": [
            {
                "title": "Implicit action reasoning separates frontier systems.",
                "detail": f"A {score_spread:.1f}-point spread separates {leading_model['name']} and {trailing_model['name']} under the same tasks, tools, step budget, and scoring protocol.",
            },
            {
                "title": "Decision quality and execution efficiency are both measurable.",
                "detail": "The official score captures end-to-end completion, while the action-recorded view isolates decision quality once an agent commits to a business action.",
            },
            {
                "title": "Cross-system evidence changes the ranking.",
                "detail": "Task-level results reveal distinct strengths across authority, financial controls, temporal validity, claims, and release governance.",
            },
            {
                "title": "Every result is traceable and reproducible.",
                "detail": "The release includes Harbor packages, deterministic assertions, model trajectories, fixed harness settings, and the exact Valkyrie run protocol.",
            },
        ],
    }


def render_page() -> str:
    data = build_page_data()
    icons = load_icons()
    complete_model = max(
        (model for model in data["models"] if model["status"] == "complete"),
        key=lambda model: model["score"],
    )
    known_costs = [
        model["cost_per_attempt"]
        for model in data["models"]
        if model["status"] == "complete" and model["cost_per_attempt"] is not None
    ]
    stats = [
        (str(len(data["models"])), "frontier models"),
        ("24", "attempts / model"),
        (f"${min(known_costs):.2f}", "lowest cost / task"),
        (f'{complete_model["score"] * 100:.1f}%', "leading official score"),
    ]
    stats_html = "".join(
        f'<div class="stat"><div class="value mono">{html.escape(value)}</div>'
        f'<div class="key">{html.escape(label)}</div></div>'
        for value, label in stats
    )
    data_blob = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    icon_blob = json.dumps(icons, ensure_ascii=False).replace("</", "<\\/")
    complete_models = [
        model for model in data["models"] if model["status"] == "complete"
    ]
    score_spread = (
        max(model["score"] for model in complete_models)
        - min(model["score"] for model in complete_models)
    ) * 100
    return (
        TEMPLATE.replace("__DATA__", data_blob)
        .replace("__ICONS__", icon_blob)
        .replace("__STATS__", stats_html)
        .replace("__MODEL_COUNT__", str(len(complete_models)))
        .replace("__SCORE_SPREAD__", f"{score_spread:.1f}")
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Destination HTML file (default: index.html)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail when the existing output differs from a fresh render.",
    )
    arguments = parser.parse_args()
    rendered = render_page()
    output = arguments.output.resolve()

    if arguments.check:
        if not output.exists() or output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"{output} is stale; run {Path(__file__).name} to regenerate it.")
        print(f"Verified {output}")
        return

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"Wrote {output}")


TEMPLATE = r"""<!doctype html>
<html lang="en" class="viz-root">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="implicit-action-bench evaluates whether AI agents recover implicit enterprise constraints before taking consequential actions.">
<meta name="theme-color" content="#FFFFFF">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<title>implicit-action-bench — Enterprise constraint-aware action benchmark</title>
<style>
.viz-root {
  color-scheme: light;
  --surface-1:#FFFFFF; --surface-2:#F7F8FA; --card:#FFFFFF; --line:#E5E7EB; --track:#F1F5F9;
  --text-primary:#111827; --text-secondary:#475569; --text-muted:#94A3B8; --accent:#4F46E5;
  --anthropic-a:#FED7C3; --anthropic-b:#F28C5C; --anthropic-c:#B9522B;
  --openai-a:#A7E3CF; --openai-b:#38A77C; --openai-c:#147A59;
  --google-a:#C7D7FE; --google-b:#7C83EE; --google-c:#4F46B8;
  --success:#147A59; --warning:#B7791F; --danger:#C2413B; --quote-bg:#111827; --quote-ink:#F8FAFC;
}
* { box-sizing:border-box; }
html { scroll-behavior:smooth; overflow-x:hidden; }
body { margin:0; background:var(--surface-1); color:var(--text-primary); font:15px/1.55 Inter,ui-sans-serif,-apple-system,"Segoe UI",Helvetica,Arial,sans-serif; -webkit-font-smoothing:antialiased; }
a { color:inherit; }
.mono { font-family:ui-monospace,"SF Mono",Menlo,Consolas,monospace; font-variant-numeric:tabular-nums; }
.wrap { max-width:1380px; margin:0 auto; padding:0 56px; }
nav.top { border-bottom:1px solid var(--line); position:sticky; top:0; z-index:5; background:color-mix(in srgb,var(--surface-1) 92%,transparent); backdrop-filter:blur(12px); }
nav.top .wrap { display:flex; align-items:center; min-height:64px; gap:36px; }
.brand { display:flex; align-items:center; gap:9px; font-weight:650; font-size:16px; letter-spacing:-.01em; text-decoration:none; }
.brand-mark { width:22px; height:22px; border-radius:6px; background:linear-gradient(135deg,#A5B4FC,var(--accent)); display:inline-block; box-shadow:inset 0 0 0 1px rgba(17,24,39,.06); }
.navlinks { display:flex; gap:30px; font-size:14px; }
.navlinks a { text-decoration:none; }
.navlinks a:hover { color:var(--accent); }
.navright { margin-left:auto; font-size:13px; border:1px solid var(--line); border-radius:6px; padding:7px 16px; text-decoration:none; }
.crumbs { font-size:12px; color:var(--text-muted); padding:14px 0; }
.crumbs b { color:var(--text-primary); font-weight:500; }
.crumbs span { margin:0 7px; }
.hero { text-align:center; padding:54px 0 44px; }
.hero h1 { font-size:56px; line-height:1.06; font-weight:450; letter-spacing:-.035em; margin:0 0 18px; }
.hero .with { color:var(--text-muted); font-size:13px; margin-bottom:22px; display:flex; gap:8px; justify-content:center; align-items:baseline; flex-wrap:wrap; }
.hero .with b { color:var(--text-primary); font-size:17px; font-weight:650; letter-spacing:-.02em; }
.hero .with .team-credit { font-size:11px; letter-spacing:.01em; }
.hero p { color:var(--text-secondary); max-width:760px; margin:0 auto 26px; font-size:16px; }
.buttons { display:flex; gap:10px; justify-content:center; }
.button { font:inherit; font-size:13px; padding:9px 18px; border-radius:6px; text-decoration:none; background:var(--surface-2); border:1px solid var(--line); }
.button.primary { background:var(--accent); color:#fff; border-color:var(--accent); font-weight:550; }
.stats { display:grid; grid-template-columns:repeat(4,1fr); padding:28px 0 82px; }
.stat { text-align:center; border-left:1px solid var(--line); padding:6px 0; }
.stat:first-child { border-left:0; }
.stat .value { font-size:44px; font-weight:400; letter-spacing:-.03em; line-height:1.15; }
.stat .key { color:var(--text-muted); font-size:17px; }
.leaderboard { display:block; padding-bottom:110px; }
.leaderboard-intro { display:grid; grid-template-columns:minmax(250px,.72fr) minmax(0,1.28fr); gap:80px; align-items:start; margin-bottom:34px; }
.section-kicker { color:var(--accent); font-size:11px; font-weight:650; text-transform:uppercase; letter-spacing:.12em; margin-bottom:10px; }
.leaderboard-intro h2 { font-size:34px; line-height:1.13; letter-spacing:-.025em; margin-bottom:0; }
.leaderboard-body { display:grid; grid-template-columns:1fr 1fr; gap:26px 42px; }
.leaderboard-body p { color:var(--text-secondary); margin:0; }
.leaderboard-body .chips { grid-column:1 / -1; margin-top:0; }
h2 { font-size:21px; font-weight:500; margin:0 0 22px; letter-spacing:-.01em; }
.chips { display:flex; gap:8px; margin-top:26px; flex-wrap:wrap; }
.chips a { font-size:13px; background:var(--surface-2); border-radius:6px; padding:6px 12px; text-decoration:none; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:32px 38px 34px; box-shadow:0 14px 44px rgba(15,23,42,.055); }
.ranking-card { margin-bottom:24px; }
.plot-card { max-width:1040px; margin:0 auto; }
.control-bar { display:flex; align-items:flex-end; justify-content:space-between; gap:16px; padding-bottom:22px; margin-bottom:8px; border-bottom:1px solid var(--line); }
.control-group > span { display:block; color:var(--text-muted); font-size:11px; text-transform:uppercase; letter-spacing:.07em; margin-bottom:7px; }
.segmented { display:inline-flex; padding:3px; gap:2px; border-radius:7px; background:var(--surface-2); border:1px solid var(--line); }
.segmented button { border:0; border-radius:5px; background:transparent; color:var(--text-secondary); font:inherit; font-size:12px; padding:6px 9px; cursor:pointer; }
.segmented button[aria-pressed="true"] { background:var(--card); color:var(--text-primary); box-shadow:0 1px 4px rgba(0,0,0,.08); }
.card-head { color:var(--text-muted); font-size:12px; margin:18px 0 5px; }
.leader-columns { display:grid; grid-template-columns:minmax(170px,1fr) 105px 92px; gap:12px; }
.leader-columns span:not(:first-child) { text-align:right; }
.leader-row { padding:13px 10px 12px; margin:0 -10px; outline:none; border-radius:8px; transition:background .18s ease; }
.leader-row:hover,.leader-row:focus-visible { background:var(--surface-2); }
.leader-top { display:grid; grid-template-columns:minmax(170px,1fr) 105px 92px; align-items:center; gap:12px; }
.model-name { font-size:16px; font-weight:500; display:flex; align-items:center; gap:7px; min-width:0; }
.model-name svg { width:16px; height:16px; fill:currentColor; flex:none; }
.model-tag { color:var(--text-muted); font-size:12.5px; font-weight:400; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.model-score,.model-metric { font-size:13px; white-space:nowrap; text-align:right; }
.model-score small { color:var(--text-muted); font-size:12.5px; margin-left:7px; }
.model-metric small { display:block; color:var(--text-muted); font-size:10px; }
.status { font-size:11px; border-radius:999px; padding:3px 8px; background:var(--surface-2); color:var(--text-muted); }
.status.complete { color:var(--success); }
.status.blocked { color:var(--warning); }
.leader-bar { position:relative; height:6px; margin-top:10px; background:var(--track); border-radius:3px; overflow:hidden; }
.leader-fill { position:absolute; inset:0 auto 0 0; border-radius:3px; }
.blocked-track { background:repeating-linear-gradient(135deg,var(--line),var(--line) 4px,var(--track) 4px,var(--track) 8px); }
.axis { position:relative; height:24px; margin-top:30px; border-top:1px solid var(--line); }
.axis span { position:absolute; top:9px; transform:translateX(-50%); color:var(--text-muted); font-size:12px; opacity:.8; }
.axis span:first-child { transform:none; }
.axis span:last-child { transform:translateX(-100%); }
.card-foot { display:flex; justify-content:space-between; align-items:center; margin-top:28px; gap:12px; color:var(--text-muted); font-size:12px; }
.plot-shell { margin:0; padding:0; }
.plot-head { display:flex; justify-content:space-between; gap:16px; align-items:baseline; margin-bottom:20px; }
.plot-head b { font-size:18px; font-weight:520; letter-spacing:-.01em; }
.plot-head span { color:var(--text-muted); font-size:12px; }
.plot-stage { position:relative; padding-left:20px; }
.plot-axis-title-y { position:absolute; left:-26px; top:50%; transform:rotate(-90deg) translateX(-50%); transform-origin:left top; color:var(--text-muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; white-space:nowrap; }
.plot-axis-title-x { color:var(--text-muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; text-align:center; margin:40px 0 0; }
.efficiency-plot { position:relative; height:390px; margin:0 24px 0 56px; border-left:1px solid var(--line); border-bottom:1px solid var(--line); background-image:linear-gradient(to top,var(--line) 1px,transparent 1px),linear-gradient(to right,var(--line) 1px,transparent 1px); background-size:100% 25%,20% 100%; }
.plot-y-label { position:absolute; left:-50px; color:var(--text-muted); font-size:11px; transform:translateY(50%); }
.plot-x-label { position:absolute; bottom:-30px; color:var(--text-muted); font-size:11px; transform:translateX(-50%); }
.plot-point { position:absolute; transform:translate(-50%,50%); display:flex; align-items:center; gap:10px; z-index:2; cursor:default; transition:z-index .15s ease; }
.plot-point:hover,.plot-point:focus-visible { z-index:4; outline:none; }
.plot-logo { width:50px; height:50px; border:1px solid var(--line); background:var(--card); border-radius:50%; display:grid; place-items:center; box-shadow:0 8px 24px rgba(0,0,0,.14); transition:transform .18s ease,box-shadow .18s ease; }
.plot-point:hover .plot-logo,.plot-point:focus-visible .plot-logo { transform:scale(1.14); box-shadow:0 12px 30px rgba(0,0,0,.20); }
.plot-logo svg { width:27px; height:27px; fill:currentColor; }
.provider-anthropic .plot-logo { color:var(--anthropic-c); border-color:color-mix(in srgb,var(--anthropic-c) 32%,var(--line)); }
.provider-openai .plot-logo { color:var(--openai-c); border-color:color-mix(in srgb,var(--openai-c) 32%,var(--line)); }
.provider-google .plot-logo { color:var(--google-c); border-color:color-mix(in srgb,var(--google-c) 32%,var(--line)); }
.plot-label { padding:6px 9px; border-radius:7px; background:color-mix(in srgb,var(--card) 94%,transparent); border:1px solid var(--line); font-size:11px; line-height:1.3; white-space:nowrap; box-shadow:0 4px 15px color-mix(in srgb,var(--text-primary) 5%,transparent); }
.plot-label b { display:block; font-size:12px; font-weight:600; }
.plot-na-band { position:absolute; right:0; top:0; bottom:0; width:19%; border-left:1px dashed var(--line); background:repeating-linear-gradient(135deg,transparent,transparent 5px,color-mix(in srgb,var(--line) 32%,transparent) 5px,color-mix(in srgb,var(--line) 32%,transparent) 6px); }
.plot-note { color:var(--text-muted); font-size:11.5px; margin-top:18px; text-align:center; }
.takeaway-layout { display:grid; grid-template-columns:1.15fr .85fr; gap:56px; align-items:start; padding-bottom:110px; }
.takeaways { list-style:none; padding:0; margin:0; counter-reset:takeaway; }
.takeaways li { counter-increment:takeaway; padding:18px 0 18px 30px; border-bottom:1px solid var(--line); position:relative; }
.takeaways li::before { content:counter(takeaway); position:absolute; left:8px; top:18px; color:var(--accent); font-size:15px; }
.takeaways b { display:block; font-weight:500; font-size:16px; margin-bottom:4px; }
.takeaways span { color:var(--text-secondary); font-size:13.5px; }
.quote { background:var(--quote-bg); color:var(--quote-ink); border-radius:10px; padding:34px 32px; margin-top:40px; }
.quote strong { display:block; font-size:42px; line-height:1; font-weight:450; letter-spacing:-.04em; }
.quote p { font-size:18px; line-height:1.45; margin:16px 0 0; }
.quote .who { margin-top:22px; font-size:13px; opacity:.7; display:flex; gap:8px; align-items:center; }
.quote svg { width:14px; height:14px; fill:currentColor; }
.section { padding:0 0 100px; }
.sub { color:var(--text-secondary); margin:-10px 0 26px; max-width:700px; }
.tabs { display:flex; gap:26px; border-bottom:1px solid var(--line); margin-bottom:30px; overflow-x:auto; }
.tabs button { font:inherit; font-size:14px; background:none; border:0; padding:0 0 10px; color:var(--text-secondary); cursor:pointer; border-bottom:2px solid transparent; margin-bottom:-1px; white-space:nowrap; }
.tabs button[aria-selected="true"] { color:var(--accent); border-bottom-color:var(--accent); }
.plain { width:100%; border-collapse:collapse; font-size:14px; }
.plain th,.plain td { text-align:left; padding:11px 8px; border-bottom:1px solid var(--line); vertical-align:middle; }
.plain th { color:var(--text-muted); font-weight:400; font-size:12.5px; }
.plain td.score { text-align:right; }
.plain th.score { text-align:right; }
.score-pill { display:inline-flex; align-items:center; justify-content:center; min-width:58px; padding:5px 8px; border-radius:5px; font-size:12px; }
.score-high { background:color-mix(in srgb,var(--success) 14%,var(--surface-1)); color:var(--success); }
.score-mid { background:color-mix(in srgb,var(--warning) 14%,var(--surface-1)); color:var(--warning); }
.score-low { background:color-mix(in srgb,var(--danger) 12%,var(--surface-1)); color:var(--danger); }
.trial-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:16px; }
.trial-card { border:1px solid var(--line); border-radius:8px; padding:18px; }
.trial-card .trial-score { font-size:32px; margin:8px 0 12px; }
.mini-track { height:7px; background:var(--track); border-radius:4px; overflow:hidden; }
.mini-track i { display:block; height:100%; background:linear-gradient(90deg,var(--anthropic-a),var(--anthropic-b)); }
.task-list { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
.task-card { border:1px solid var(--line); border-radius:8px; padding:18px; }
.task-meta { display:flex; justify-content:space-between; gap:12px; color:var(--text-muted); font-size:12px; margin-bottom:8px; }
.task-card h3 { font-size:16px; margin:0 0 6px; font-weight:550; }
.task-card p { color:var(--text-secondary); font-size:13px; margin:0 0 12px; }
.task-card details { border-top:1px solid var(--line); padding-top:10px; }
.task-card summary { cursor:pointer; color:var(--accent); font-size:12px; }
.task-card details p { margin:10px 0 0; }
.trajectory-list { display:grid; gap:14px; }
.trajectory { border:1px solid var(--line); border-radius:10px; padding:22px; display:grid; grid-template-columns:180px 1fr; gap:26px; }
.trajectory .eyebrow { color:var(--text-muted); font-size:11px; text-transform:uppercase; letter-spacing:.08em; }
.trajectory h3 { font-size:17px; font-weight:550; margin:5px 0 8px; }
.trajectory p { color:var(--text-secondary); margin:0 0 10px; }
.trajectory code { color:var(--text-muted); font-size:11px; overflow-wrap:anywhere; }
.method { color:var(--text-secondary); font-size:14px; max-width:860px; }
.method p { margin:0 0 14px; }
.method b { color:var(--text-primary); font-weight:500; }
.method-callout { border-left:3px solid var(--accent); padding:12px 16px; background:var(--surface-2); border-radius:0 7px 7px 0; margin:24px 0; }
footer { border-top:1px solid var(--line); color:var(--text-muted); font-size:12px; padding:22px 0 40px; }
.tip { position:fixed; pointer-events:none; background:var(--text-primary); color:var(--surface-1); font-size:12.5px; padding:10px 12px; border-radius:10px; max-width:360px; line-height:1.45; z-index:9; box-shadow:0 16px 50px rgba(0,0,0,.24); }
.tip.model-tip { width:340px; max-width:calc(100vw - 24px); padding:17px; border:1px solid color-mix(in srgb,var(--surface-1) 15%,transparent); }
.tip-head { display:flex; align-items:center; gap:11px; padding-bottom:13px; border-bottom:1px solid color-mix(in srgb,var(--surface-1) 18%,transparent); }
.tip-head .tip-logo { width:34px; height:34px; border-radius:50%; background:var(--surface-1); color:var(--text-primary); display:grid; place-items:center; flex:none; }
.tip-head svg { width:19px; height:19px; fill:currentColor; }
.tip-head b { display:block; font-size:14px; line-height:1.25; }
.tip-head span { display:block; opacity:.65; font-size:11px; margin-top:2px; }
.tip-primary { display:flex; justify-content:space-between; align-items:end; gap:14px; padding:14px 0 12px; }
.tip-primary span { opacity:.65; font-size:11px; text-transform:uppercase; letter-spacing:.07em; }
.tip-primary strong { display:block; font-size:29px; line-height:1; font-weight:520; letter-spacing:-.04em; }
.tip-primary small { opacity:.65; font-size:11px; }
.tip-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }
.tip-metric { background:color-mix(in srgb,var(--surface-1) 9%,transparent); border-radius:7px; padding:9px 10px; }
.tip-metric span { display:block; opacity:.62; font-size:10px; margin-bottom:2px; }
.tip-metric b { font-size:12px; font-weight:550; }
[hidden] { display:none !important; }
@media (max-width:920px) {
  .takeaway-layout { grid-template-columns:1fr; }
  .leaderboard-intro { grid-template-columns:1fr; gap:20px; }
  .leaderboard-body { grid-template-columns:1fr; gap:14px; }
  .leaderboard-body .chips { grid-column:auto; }
  .stats { grid-template-columns:repeat(2,1fr); row-gap:24px; }
  .stat:nth-child(3) { border-left:0; }
  .hero h1 { font-size:36px; }
  .navlinks { display:none; }
  .wrap { padding:0 22px; }
  .task-list { grid-template-columns:1fr; }
  .efficiency-plot { height:360px; margin-right:6px; }
}
@media (max-width:620px) {
  body { width:100vw; max-width:100vw; overflow-x:hidden; }
  .wrap { width:100vw; max-width:100vw; }
  .hero,.stats,.leaderboard,.leaderboard-intro,.leaderboard-body,.card,.plot-shell { width:100%; max-width:100%; min-width:0; }
  .leaderboard-intro > *,.leaderboard-body > * { min-width:0; }
  .navright { display:none; }
  .stats { grid-template-columns:1fr 1fr; }
  .stat .value { font-size:34px; }
  .stat .key { font-size:14px; }
  .hero h1 { font-size:32px; overflow-wrap:anywhere; }
  .hero h1 br { display:none; }
  .leaderboard-intro h2 { font-size:30px; overflow-wrap:anywhere; }
  .trial-grid { grid-template-columns:1fr; }
  .trajectory { grid-template-columns:1fr; gap:10px; }
  .table-scroll { overflow-x:auto; }
  .control-bar { align-items:stretch; flex-direction:column; }
  .leader-columns,.leader-top { grid-template-columns:minmax(0,1fr) 104px; gap:9px; }
  .leader-columns span:nth-child(3),.model-metric { display:none; }
  .model-name { font-size:14px; }
  .model-score small { display:none; }
  .model-tag { display:none; }
  .card { padding:24px 18px 26px; }
  .plot-head { align-items:flex-start; flex-direction:column; }
  .plot-stage { padding-left:0; }
  .plot-axis-title-y { display:none; }
  .efficiency-plot { margin-left:38px; height:300px; }
  .plot-label { display:none; }
  .plot-logo { width:42px; height:42px; }
  .plot-logo svg { width:23px; height:23px; }
  .plot-shell { overflow:hidden; }
}
</style>
</head>
<body>
<nav class="top"><div class="wrap">
  <a class="brand" href="#"><span class="brand-mark"></span>implicit-action-bench</a>
  <div class="navlinks"><a href="#leaderboard">Leaderboard</a><a href="#results">Results</a><a href="#trajectories">Trajectories</a><a href="#method">Methodology</a><a href="#takeaways">Takeaways</a></div>
  <a class="navright" href="#method">Research release</a>
</div></nav>
<main class="wrap">
  <div class="crumbs">Home<span>›</span>Benchmarks<span>›</span><b>implicit-action-bench</b></div>

  <section class="hero">
    <h1>The benchmark for actions shaped<br>by rules nobody states.</h1>
    <div class="with">Built on <b>Valkyrie</b><span>·</span><b>mini-SWE-agent</b><span class="team-credit">· by Yaya &amp; Vivi team</span></div>
    <p>implicit-action-bench measures whether frontier agents can recover company-specific constraints from realistic enterprise evidence and take the right consequential action.</p>
    <div class="buttons"><a class="button primary" href="#leaderboard">Explore leaderboard</a><a class="button" href="#method">Read methodology</a></div>
  </section>

  <section class="stats">__STATS__</section>

  <section class="leaderboard" id="leaderboard">
    <div class="leaderboard-intro">
      <div><div class="section-kicker">Enterprise action intelligence</div><h2>The implicit-action-bench leaderboard</h2></div>
      <div class="leaderboard-body">
        <p>Eight high-context tasks are grounded in the Redwood Inference world from EnterpriseRAG-Bench. Each sandbox contains at least 120 authentic records plus current-decision overlays, requiring models to reconstruct the controlling rule from a realistic evidence neighborhood.</p>
        <p>The official score measures end-to-end success: evidence discovery, constraint resolution, and useful action. The action-recorded view offers a complementary lens on decision quality once a model commits to an action.</p>
        <div class="chips"><a href="#results">Task results</a><a href="#trajectories">Trajectory evidence</a><a href="#takeaways">Research insights</a></div>
      </div>
    </div>
    <div class="card ranking-card">
      <div class="control-bar">
        <div class="control-group"><span>Score view</span><div class="segmented" id="score-toggle"><button type="button" data-score-mode="raw" aria-pressed="true">Official score</button><button type="button" data-score-mode="actionful" aria-pressed="false">Action recorded</button></div></div>
        <div class="control-group"><span>Efficiency axis</span><div class="segmented" id="metric-toggle"><button type="button" data-metric="cost" aria-pressed="true">Cost</button><button type="button" data-metric="time" aria-pressed="false">Time</button></div></div>
      </div>
      <div class="card-head leader-columns"><span>Model</span><span id="score-head">Official score</span><span id="metric-head">Cost / task</span></div>
      <div id="leader-rows"></div>
      <div class="axis" id="axis"></div>
      <div class="card-foot"><span>Official and action-recorded rankings</span><span class="mono">24 attempts / model</span></div>
    </div>
    <div class="card plot-card">
      <div class="plot-shell">
        <div class="plot-head"><b id="plot-title">Official success vs. cost</b><span>Hover or focus a model for complete results</span></div>
        <div class="plot-stage"><span class="plot-axis-title-y">Success rate</span><div class="efficiency-plot" id="efficiency-plot"></div></div>
        <div class="plot-axis-title-x" id="plot-axis-title-x">Average API cost per task attempt</div>
        <div class="plot-note" id="plot-note"></div>
      </div>
      <div class="card-foot"><span>3 trials × 8 tasks × __MODEL_COUNT__ frontier models</span><span class="mono">release 1.0</span></div>
    </div>
  </section>

  <section class="takeaway-layout" id="takeaways">
    <div><h2>Research insights</h2><ol class="takeaways" id="takeaway-list"></ol></div>
    <aside class="quote">
      <strong class="mono" id="quote-score"></strong>
      <p>Leading end-to-end score across 24 independent task attempts.</p>
      <div class="who"><span id="quote-icon"></span><span id="quote-model"></span> · fixed harness and benchmark release</div>
    </aside>
  </section>

  <section class="section" id="results">
    <h2>Results</h2>
    <p class="sub">Explore task-level performance, repeated trials, system efficiency, and the complete benchmark task library under one fixed protocol.</p>
    <div class="tabs" role="tablist">
      <button role="tab" aria-selected="true" data-tab="task-panel">By task</button>
      <button role="tab" aria-selected="false" data-tab="trial-panel">Trials</button>
      <button role="tab" aria-selected="false" data-tab="system-panel">Systems</button>
      <button role="tab" aria-selected="false" data-tab="task-library-panel">Task library</button>
    </div>
    <div id="task-panel" class="table-scroll"><table class="plain" id="task-table"></table></div>
    <div id="trial-panel" hidden><div class="trial-grid" id="trial-grid"></div></div>
    <div id="system-panel" hidden class="table-scroll"><table class="plain" id="system-table"></table></div>
    <div id="task-library-panel" hidden><div class="task-list" id="task-list"></div></div>
  </section>

  <section class="section" id="trajectories">
    <h2>Representative trajectories</h2>
    <p class="sub">Concrete examples show how frontier agents discover evidence, reconcile implicit constraints, and translate reasoning into business actions.</p>
    <div class="trajectory-list" id="trajectory-list"></div>
  </section>

  <section class="section method" id="method">
    <h2>Methodology</h2>
    <p><b>Enterprise setting.</b> Every task starts from the same pinned EnterpriseRAG-Bench company world, then adds a small decision overlay. Agents search ordinary Slack, Gmail, CRM, Jira, Drive, and engineering records; no file is labeled as gold evidence or distractor.</p>
    <p><b>Implicit constraints.</b> No single record states the complete rule. The correct action joins scope, authority, timing, evidence, or system-of-record facts across multiple sources. Distractors are recent and credible but do not control the final decision.</p>
    <p><b>Shared harness.</b> Anthropic, OpenAI, and Google models use the same mini-SWE-agent package, system-prompt structure, business-action tool catalog, 25-step cap, and three independent trials. Task sandboxes have no public internet access.</p>
    <div class="method-callout mono">score = 0 if a forbidden action occurs<br>otherwise 60% deterministic + 20% awareness + 20% alternative quality</div>
    <p><b>Interpretation.</b> Full pass requires every scoring component. Partial credit is included in the mean. Standard deviation is calculated across the three complete trial means, and blocked providers remain unscored.</p>
    <p><b>Research contribution.</b> The benchmark jointly measures decision quality and execution efficiency. The __SCORE_SPREAD__-point frontier-model spread, task-specific ranking reversals, and action-recorded comparison expose capabilities that aggregate question-answering evaluations do not capture.</p>
  </section>
</main>
<footer><div class="wrap">implicit-action-bench · Enterprise constraint-aware action benchmark · built on Valkyrie</div></footer>
<div class="tip" hidden></div>
<script>
const theme = new URLSearchParams(location.search).get("theme");
if (theme) document.documentElement.dataset.theme = theme;
const DATA = __DATA__;
const ICONS = __ICONS__;
const PROVIDER_TOKEN = {Anthropic:"anthropic", OpenAI:"openai", Google:"google"};
const percent = value => value == null ? "N/A" : `${(value * 100).toFixed(1)}%`;
let scoreMode = "raw";
let efficiencyMetric = "cost";
const escapeHtml = value => String(value).replace(/[&<>"]/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"})[character]);

function scoreClass(value) {
  if (value >= .75) return "score-high";
  if (value >= .5) return "score-mid";
  return "score-low";
}

function displayedScore(model) {
  return scoreMode === "raw" ? model.score : model.actionful_mean;
}

function displayedStddev(model) {
  return scoreMode === "raw" ? model.stddev : model.actionful_stddev;
}

function metricValue(model) {
  return efficiencyMetric === "cost" ? model.cost_per_attempt : model.mean_agent_minutes;
}

function metricLabel(model) {
  const value = metricValue(model);
  if (value == null) return "not reported";
  return efficiencyMetric === "cost" ? `$${value.toFixed(2)}` : `${value.toFixed(1)} min`;
}

function renderEfficiencyPlot(models) {
  const plot = document.getElementById("efficiency-plot");
  const scored = models.filter(model => model.status === "complete" && displayedScore(model) != null);
  const known = scored.filter(model => metricValue(model) != null);
  const hasMissing = known.length !== scored.length;
  const values = known.map(metricValue);
  const maxValue = Math.max(...values);
  const minValue = Math.min(...values);
  const costMin = minValue * .82;
  const costMax = maxValue * 1.22;
  const timeMax = maxValue * 1.16;
  const usableWidth = hasMissing && efficiencyMetric === "cost" ? 68 : 84;
  const xPosition = model => {
    const value = metricValue(model);
    if (value == null) return 91;
    if (efficiencyMetric === "cost") {
      const denominator = Math.log(costMax) - Math.log(costMin) || 1;
      return 8 + ((Math.log(value) - Math.log(costMin)) / denominator) * usableWidth;
    }
    return 8 + (value / timeMax) * usableWidth;
  };
  const yLabels = [0,25,50,75,100].map(value => `<span class="plot-y-label mono" style="bottom:${value}%">${value}%</span>`).join("");
  const xTicks = efficiencyMetric === "cost"
    ? [costMin, Math.sqrt(costMin * costMax), costMax]
    : [0, timeMax / 2, timeMax];
  const xLabels = xTicks.map(value => {
    const position = efficiencyMetric === "cost"
      ? 8 + ((Math.log(value) - Math.log(costMin)) / (Math.log(costMax) - Math.log(costMin) || 1)) * usableWidth
      : 8 + (value / timeMax) * usableWidth;
    const label = efficiencyMetric === "cost" ? `$${value.toFixed(2)}` : `${value.toFixed(1)}m`;
    return `<span class="plot-x-label mono" style="left:${position}%">${label}</span>`;
  }).join("");
  const missingBand = hasMissing && efficiencyMetric === "cost" ? `<div class="plot-na-band"><span class="plot-x-label mono" style="left:50%">not reported</span></div>` : "";
  const points = scored.map(model => {
    const score = displayedScore(model);
    const x = xPosition(model);
    const token = PROVIDER_TOKEN[model.provider] || "google";
    const reverse = x > 72 ? "flex-direction:row-reverse" : "";
    const label = `${model.name}, ${scoreMode === "raw" ? "official" : "action-recorded"} score ${percent(score)}, ${metricLabel(model)}`;
    return `<div class="plot-point provider-${token}" tabindex="0" aria-label="${escapeHtml(label)}" style="left:${x}%;bottom:${score * 100}%;${reverse}" data-model-id="${escapeHtml(model.id)}"><span class="plot-logo">${ICONS[model.provider] || ""}</span><span class="plot-label"><b>${escapeHtml(model.name)}</b>${percent(score)} · ${metricLabel(model)}</span></div>`;
  }).join("");
  plot.innerHTML = `${yLabels}${xLabels}${missingBand}${points}`;
  document.getElementById("plot-title").textContent = `${scoreMode === "raw" ? "Official success" : "Action-recorded success"} vs. ${efficiencyMetric === "cost" ? "API cost / task" : "mean agent time"}`;
  document.getElementById("plot-axis-title-x").textContent = efficiencyMetric === "cost" ? "Average API cost per task attempt" : "Mean agent execution time per task attempt";
  document.getElementById("plot-note").textContent = efficiencyMetric === "cost"
    ? "Cost is averaged across 24 attempts. Gemini Carbon is estimated from €11.47 total account spend (≈ $12.68 at EUR 1 = USD 1.1052, ECB 13 Nov 2026), or about $0.53 per task."
    : "Time is mean model-agent execution time per task attempt; sandbox setup and queue time are excluded.";
}

function renderLeaderboard() {
  const rows = [...DATA.models].sort((left, right) => {
    const leftScore = displayedScore(left);
    const rightScore = displayedScore(right);
    if (leftScore == null && rightScore == null) return left.name.localeCompare(right.name);
    if (leftScore == null) return 1;
    if (rightScore == null) return -1;
    return rightScore - leftScore;
  });
  document.getElementById("leader-rows").innerHTML = rows.map(model => {
    const token = PROVIDER_TOKEN[model.provider] || "google";
    const complete = model.status === "complete";
    const score = displayedScore(model);
    const stddev = displayedStddev(model);
    const value = complete ? `${percent(score)}<small>± ${(stddev * 100).toFixed(1)} pp</small>` : `<span class="status blocked">quota blocked</span>`;
    const bar = complete
      ? `<div class="leader-fill" style="width:${Math.max(score * 100, .8)}%;background:linear-gradient(90deg,var(--${token}-a),var(--${token}-b))"></div>`
      : "";
    return `<div class="leader-row" tabindex="0" data-model-id="${escapeHtml(model.id)}">
      <div class="leader-top"><span class="model-name">${ICONS[model.provider] || ""}${escapeHtml(model.name)}<span class="model-tag">${escapeHtml(model.provider)}</span></span><span class="model-score mono">${value}</span><span class="model-metric mono">${metricLabel(model)}<small>${efficiencyMetric === "cost" ? (model.cost_type?.startsWith("estimated") ? "estimated" : "per task") : "mean agent"}</small></span></div>
      <div class="leader-bar ${complete ? "" : "blocked-track"}">${bar}</div>
    </div>`;
  }).join("");
  document.getElementById("axis").innerHTML = [0,20,40,60,80,100].map(value => `<span style="left:${value}%">${value}%</span>`).join("");
  document.getElementById("score-head").textContent = scoreMode === "raw" ? "Official score" : "Action score";
  document.getElementById("metric-head").textContent = efficiencyMetric === "cost" ? "Cost / task" : "Mean time";
  renderEfficiencyPlot(rows);
  bindTooltips();
}

function bindLeaderboardControls() {
  document.querySelectorAll("[data-score-mode]").forEach(button => button.addEventListener("click", () => {
    scoreMode = button.dataset.scoreMode;
    document.querySelectorAll("[data-score-mode]").forEach(item => item.setAttribute("aria-pressed", String(item === button)));
    renderLeaderboard();
  }));
  document.querySelectorAll("[data-metric]").forEach(button => button.addEventListener("click", () => {
    efficiencyMetric = button.dataset.metric;
    document.querySelectorAll("[data-metric]").forEach(item => item.setAttribute("aria-pressed", String(item === button)));
    renderLeaderboard();
  }));
}

function renderTakeaways() {
  document.getElementById("takeaway-list").innerHTML = DATA.takeaways.map(item => `<li><b>${escapeHtml(item.title)}</b><span>${escapeHtml(item.detail)}</span></li>`).join("");
  const leader = DATA.models.filter(model => model.status === "complete").sort((left, right) => right.score - left.score)[0];
  document.getElementById("quote-score").textContent = percent(leader.score);
  document.getElementById("quote-model").textContent = leader.name;
  document.getElementById("quote-icon").innerHTML = ICONS[leader.provider] || "";
}

function renderTaskTable() {
  const completeModels = DATA.models.filter(model => model.status === "complete").sort((left, right) => right.score - left.score);
  const modelHeaders = completeModels.map(model => `<th class="score">${escapeHtml(model.name)}</th>`).join("");
  document.getElementById("task-table").innerHTML = `<thead><tr><th>Task</th><th>Constraint family</th>${modelHeaders}<th class="score">Score range</th></tr></thead><tbody>${DATA.tasks.map(task => {
    const modelCells = completeModels.map(model => {
      const result = task.model_results[model.id];
      return `<td class="score"><span class="score-pill ${scoreClass(result.mean)} mono" data-tip="${escapeHtml(`${model.name}|Trials: ${result.scores.map(percent).join(", ")}|SD ${(result.stddev * 100).toFixed(1)} pp`)}">${percent(result.mean)}</span></td>`;
    }).join("");
    const scores = completeModels.map(model => task.model_results[model.id].mean);
    const delta = (Math.max(...scores) - Math.min(...scores)) * 100;
    return `<tr>
    <td><b>${escapeHtml(task.title)}</b><br><small class="mono">${escapeHtml(task.id)}</small></td>
    <td>${escapeHtml(task.category)}</td>
    ${modelCells}<td class="score mono">${delta.toFixed(1)} pp</td>
  </tr>`;}).join("")}</tbody>`;
}

function renderTrials() {
  const completeModels = DATA.models.filter(model => model.status === "complete").sort((left, right) => right.score - left.score);
  document.getElementById("trial-grid").innerHTML = completeModels.flatMap(model => model.trial_scores.map((score, index) => {
    const token = PROVIDER_TOKEN[model.provider] || "google";
    return `<article class="trial-card">
      <span class="model-name">${ICONS[model.provider] || ""}${escapeHtml(model.name)}</span><div class="trial-score mono">${percent(score)}</div>
      <div class="mini-track"><i style="width:${score * 100}%;background:linear-gradient(90deg,var(--${token}-a),var(--${token}-b))"></i></div><p>Trial ${index + 1} · 8 independent tasks</p>
      <small class="mono">${escapeHtml(model.run_ids[index])}</small>
    </article>`;
  })).join("");
}

function renderSystems() {
  const models = [...DATA.models].sort((left, right) => (right.score ?? -1) - (left.score ?? -1));
  document.getElementById("system-table").innerHTML = `<thead><tr><th>Model</th><th>Provider</th><th>Status</th><th class="score">Attempts</th><th class="score">Full pass</th><th class="score">API cost</th></tr></thead><tbody>${models.map(model => `<tr>
    <td><span class="model-name">${ICONS[model.provider] || ""}${escapeHtml(model.name)}</span></td><td>${escapeHtml(model.provider)}</td>
    <td><span class="status ${model.status === "complete" ? "complete" : "blocked"}">${model.status === "complete" ? "complete" : "quota blocked"}</span></td>
    <td class="score mono">${model.status === "complete" ? `${model.attempts}/24` : "0/24"}</td><td class="score mono">${percent(model.pass_rate)}</td>
    <td class="score mono">${model.cost_usd == null ? "not reported" : `$${model.cost_usd.toFixed(2)} ${model.cost_type}`}</td>
  </tr>`).join("")}</tbody>`;
}

function renderTaskLibrary() {
  const completeModels = DATA.models.filter(model => model.status === "complete").sort((left, right) => right.score - left.score);
  document.getElementById("task-list").innerHTML = DATA.tasks.map(task => `<article class="task-card">
    <div class="task-meta"><span>${escapeHtml(task.category)}</span><span class="mono">${completeModels.map(model => `${escapeHtml(model.name.replace(/^(Claude|GPT-6|Gemini 4) /, ""))} ${percent(task.model_results[model.id].mean)}`).join(" · ")}</span></div>
    <h3>${escapeHtml(task.title)}</h3><p><b>${escapeHtml(task.role)}</b> · ${escapeHtml(task.objective)}</p>
    <details><summary>View explicit final instruction</summary><p>${escapeHtml(task.instruction)}</p></details>
  </article>`).join("");
}

function renderTrajectories() {
  document.getElementById("trajectory-list").innerHTML = DATA.trajectories.map(example => `<article class="trajectory">
    <div><div class="eyebrow">${escapeHtml(example.classification.replaceAll("_", " "))}</div><h3>${escapeHtml(example.task_id.replace("redwood-", "").replaceAll("-", " "))}</h3><span class="score-pill ${scoreClass(example.score)} mono">${percent(example.score)}</span></div>
    <div><p><b>Observed.</b> ${escapeHtml(example.observed)}</p><p><b>Why it matters.</b> ${escapeHtml(example.why_interesting)}</p><code>${escapeHtml(example.trajectory)}</code></div>
  </article>`).join("");
}

function modelTooltipMarkup(model) {
  const selectedScore = displayedScore(model);
  const selectedStddev = displayedStddev(model);
  const scoreLabel = scoreMode === "raw" ? "Official score" : "Action-recorded score";
  const cost = model.cost_per_attempt == null ? "Unpriced" : `$${model.cost_per_attempt.toFixed(2)} / task${model.cost_type?.startsWith("estimated") ? " · est." : ""}`;
  return `<div class="tip-head"><span class="tip-logo">${ICONS[model.provider] || ""}</span><div><b>${escapeHtml(model.name)}</b><span>${escapeHtml(model.provider)} · mini-SWE-agent</span></div></div>
    <div class="tip-primary"><div><span>${scoreLabel}</span><strong class="mono">${percent(selectedScore)}</strong></div><small class="mono">± ${(selectedStddev * 100).toFixed(1)} pp</small></div>
    <div class="tip-grid">
      <div class="tip-metric"><span>Official score</span><b class="mono">${percent(model.score)}</b></div>
      <div class="tip-metric"><span>Action recorded</span><b class="mono">${percent(model.actionful_mean)}</b></div>
      <div class="tip-metric"><span>Full pass</span><b class="mono">${percent(model.pass_rate)}</b></div>
      <div class="tip-metric"><span>Recorded actions</span><b class="mono">${model.actionful_runs}/${model.attempts}</b></div>
      <div class="tip-metric"><span>Average cost</span><b class="mono">${cost}</b></div>
      <div class="tip-metric"><span>Mean time</span><b class="mono">${model.mean_agent_minutes.toFixed(1)} min</b></div>
    </div>`;
}

function bindTabs() {
  document.querySelectorAll("[role=tab]").forEach(button => button.addEventListener("click", () => {
    document.querySelectorAll("[role=tab]").forEach(tab => tab.setAttribute("aria-selected", String(tab === button)));
    ["task-panel","trial-panel","system-panel","task-library-panel"].forEach(panelId => document.getElementById(panelId).hidden = panelId !== button.dataset.tab);
    const params = new URLSearchParams(location.search);
    params.set("tab", button.dataset.tab);
    history.replaceState(null, "", `${location.pathname}?${params}${location.hash}`);
  }));
  const requestedTab = new URLSearchParams(location.search).get("tab");
  const requestedButton = requestedTab && document.querySelector(`[data-tab="${requestedTab}"]`);
  if (requestedButton) requestedButton.click();
}

function bindTooltips() {
  const tooltip = document.querySelector(".tip");
  document.querySelectorAll("[data-tip]:not([data-tip-bound]),[data-model-id]:not([data-tip-bound])").forEach(element => {
    element.dataset.tipBound = "true";
    const show = event => {
      const model = element.dataset.modelId ? DATA.models.find(item => item.id === element.dataset.modelId) : null;
      tooltip.classList.toggle("model-tip", Boolean(model));
      if (model) {
        tooltip.innerHTML = modelTooltipMarkup(model);
      } else {
        const lines = element.dataset.tip.split("|");
        tooltip.innerHTML = `<b>${escapeHtml(lines.shift())}</b>${lines.map(line => escapeHtml(line)).join("<br>")}`;
      }
      tooltip.hidden = false;
      const left = Math.min(event.clientX + 14, innerWidth - tooltip.offsetWidth - 12);
      const top = Math.min(event.clientY + 14, innerHeight - tooltip.offsetHeight - 12);
      tooltip.style.left = `${Math.max(12, left)}px`;
      tooltip.style.top = `${Math.max(12, top)}px`;
    };
    element.addEventListener("mousemove", show);
    element.addEventListener("mouseenter", show);
    element.addEventListener("mouseleave", () => tooltip.hidden = true);
    element.addEventListener("focus", () => {
      const bounds = element.getBoundingClientRect();
      show({clientX: bounds.left, clientY: bounds.bottom});
    });
    element.addEventListener("blur", () => tooltip.hidden = true);
  });
}

bindLeaderboardControls();
renderLeaderboard();
renderTakeaways();
renderTaskTable();
renderTrials();
renderSystems();
renderTaskLibrary();
renderTrajectories();
bindTabs();
bindTooltips();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
