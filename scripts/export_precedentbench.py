#!/usr/bin/env python3
"""Export PrecedentBench results (the "rule only in the team's habits" part) for this page.

    python3 scripts/export_precedentbench.py [path/to/vals-hack/results]

Reads PrecedentBench's per-try results (morning_v3.json) and writes
results/precedentbench/summary.json. Only the hardest honest setting is shown:
8 habits (with and without last year's policy doc), 3 examples per habit,
whole morning right (every one of 15 invoices). Mean score = share of invoices right.
The told control (all 8 habits stated in the instruction) is the fairness line.

`jobs` is keyed by job so refunds can be added later as a second job.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import math
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results" / "precedentbench"
DEFAULT_SRC = ROOT.parent / "vals-hack" / "results"

MODELS = {
    "claude-fable-5-2": ("anthropic/claude-fable-5-2", "Claude Fable 5.2", "Anthropic"),
    "claude-opus-5-5": ("anthropic/claude-opus-5-5", "Claude Opus 5.5", "Anthropic"),
    "claude-sonnet-5-5": ("anthropic/claude-sonnet-5-5", "Claude Sonnet 5.5", "Anthropic"),
    "gpt-6.1-sol": ("openai/gpt-6.1-sol", "GPT-6.1 Sol", "OpenAI"),
    "gpt-6-astra": ("openai/gpt-6-astra", "GPT-6 Astra", "OpenAI"),
}
MAIN_VERSIONS = ("morningL2-k3-nohandbook", "morningL2-k3-handbook")
TOLD_VERSION = "morningL2-k3-told"


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if not n:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


def boot(xs: list[float], reps: int = 10000) -> tuple[float, float]:
    if not xs:
        return 0.0, 0.0
    rng = random.Random(0)
    ms = sorted(sum(rng.choice(xs) for _ in xs) / len(xs) for _ in range(reps))
    return ms[int(.025 * reps)], ms[int(.975 * reps) - 1]


def stats(rows: list[dict]) -> dict:
    n = len(rows)
    k = sum(r["reward"] == 1 for r in rows)
    means = [r["reward"] for r in rows]
    lo, hi = wilson(k, n)
    mlo, mhi = boot(means)
    return {"n": n, "k": k, "pass": k / n if n else None, "pass_lo": lo, "pass_hi": hi,
            "mean": sum(means) / n if n else None, "mean_lo": mlo, "mean_hi": mhi}


CARDS = [
    {"label": "Thin evidence", "model": "Claude Fable 5.2", "setting": "8 habits, 3 examples each",
     "observed": "Got 13 of 15 invoices right, but flagged two mid-size invoices for review: with only three rows "
                 "showing the new $10,000 cutoff, it kept the old $5,000 one in case the recent rows were slips.",
     "why": "The same model is near perfect when each habit is shown five times. With many habits and thin "
            "evidence, even the strongest agent holds on to the old way.",
     "run": "valkyrie run 4d0d826e-e060-4dbd-b54d-63c2253b3303 · morningL2-k3-nohandbook-r5"},
    {"label": "Reads the history like a spreadsheet", "model": "GPT-6.1 Sol", "setting": "8 habits, 3 examples each",
     "observed": "Wrote a short Python script that walked all three quarterly trackers and counted, per supplier, "
                 "cost centers, who logged it and the review notes. Then logged all 15 invoices correctly, "
                 "including the re-sent invoice marked DUPLICATE - do not pay.",
     "why": "Every model has the same terminal and tools. Choosing to analyze the history systematically is part "
            "of the skill, and it is why Sol leads at three examples.",
     "run": "valkyrie run 9df3920d-731c-4ea3-9de5-afae905b3b0a · morningL2-k3-nohandbook-r4"},
    {"label": "Misses the newest habit", "model": "GPT-6 Astra", "setting": "8 habits, 3 examples each",
     "observed": "Caught the duplicate and the new reviewers, but left the small Kellerby and Pellham invoices "
                 "blank instead of noting \"card\", a habit that only started on October 19.",
     "why": "The most recent change, with the fewest rows behind it, is the one that slips.",
     "run": "valkyrie run adbb1b8c-1b0b-4966-b430-f31515e131d5 · morningL2-k3-nohandbook-r5"},
    {"label": "Follows when told, not when inferring", "model": "Claude Opus 5.5", "setting": "8 habits, 5 examples each",
     "observed": "Read most habits correctly but would not write \"PO matched\": \"I couldn't check purchase orders, "
                 "so the Infra invoices have no PO note.\" Told the 8 habits in plain words, Opus and Sonnet get "
                 "every try fully right.",
     "why": "They can follow the team's rules. They do not pick them up from how the team works.",
     "run": "valkyrie run de093376-839d-4b50-bd9c-74af6b064d20 · morningL2-k5-nohandbook-r5"},
]


def agent_seconds(rows: list[dict]) -> dict[str, float]:
    """Wall time of the agent per attempt, from the plain agent's own "end" log event (cached)."""
    cache_path = OUT_DIR / "timing_cache.json"
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    todo = [r for r in rows if f"{r['run_id']}|{r['task']}" not in cache]

    def fetch(r: dict) -> tuple[str, float | None]:
        out = subprocess.run(["valkyrie", "run", "logs", r["run_id"], "--task-id", r["task"]],
                             capture_output=True, text=True, cwd="/tmp").stdout
        secs = None
        for line in out.splitlines():
            i = line.find("{")
            if i < 0 or '"end"' not in line:
                continue
            try:
                e = json.loads(line[i:])
            except json.JSONDecodeError:
                continue
            if e.get("type") == "end" and e.get("seconds") is not None:
                secs = float(e["seconds"])
        return f"{r['run_id']}|{r['task']}", secs

    with cf.ThreadPoolExecutor(20) as pool:
        for key, secs in pool.map(fetch, todo):
            cache[key] = secs
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(cache, indent=1))
    return cache


def level_pass(rows: list[dict], versions_pred) -> dict:
    xs = [r for r in rows if versions_pred(r)]
    k = sum(r["reward"] == 1 for r in xs)
    return {"k": k, "n": len(xs)}


def main() -> None:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    rows = [r for r in json.loads((src / "morning_v3.json").read_text())
            if r.get("status") == "FINISHED" and r.get("reward") is not None]
    models = []
    for key, (mid, name, provider) in MODELS.items():
        main_rows = [r for r in rows if r["model"] == key and r.get("version") in MAIN_VERSIONS]
        told_rows = [r for r in rows if r["model"] == key and r.get("version") == TOLD_VERSION]
        models.append({"id": mid, "name": name, "provider": provider,
                       "main": stats(main_rows), "told": stats(told_rows), "_rows": main_rows})
    timing = agent_seconds([r for m in models for r in m["_rows"]])
    for m in models:
        secs = [timing.get(f"{r['run_id']}|{r['task']}") for r in m.pop("_rows")]
        secs = [x for x in secs if x is not None]
        m["mean_agent_minutes"] = sum(secs) / len(secs) / 60 if secs else None
    top3 = ("gpt-6.1-sol", "claude-fable-5-2", "gpt-6-astra")
    four = level_pass(rows, lambda r: r["model"] in top3 and r.get("version", "").startswith("morning3-")
                      and not r.get("handbook") and not r.get("told") and r.get("dose") == 3)
    eight = level_pass(rows, lambda r: r["model"] in top3 and r.get("version") in MAIN_VERSIONS)
    told_k = sum(m["told"]["k"] for m in models)
    told_n = sum(m["told"]["n"] for m in models)
    out = {
        "benchmark": "PrecedentBench",
        "jobs": {
            "invoices": {
                "title": "Supplier invoices",
                "setting": "8 habits (with and without last year's policy doc), 3 examples per habit",
                "metric": "whole morning right: all 15 invoices",
                "models": models,
                "told": {"k": told_k, "n": told_n},
                "top3_four_rules": four,
                "top3_eight_rules": eight,
                "cards": CARDS,
            },
            # "refunds": {...}  (second job, added later in the same shape)
        },
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "summary.json").write_text(json.dumps(out, indent=1))
    for m in models:
        print(f"{m['name']:18s} {m['main']['k']}/{m['main']['n']} whole job right, "
              f"{m['main']['mean'] * 100:.1f}% invoices right, told {m['told']['k']}/{m['told']['n']}")
    print(f"told total {told_k}/{told_n}")


if __name__ == "__main__":
    main()
