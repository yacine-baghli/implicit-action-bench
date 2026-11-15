#!/usr/bin/env python3
"""Merge completed Valkyrie trials into the published comparison summary."""

from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUMMARY = ROOT / "results" / "comparison-v3" / "summary.json"
USAGE_FIELDS = (
    "prompt_tokens",
    "completion_tokens",
    "cached_tokens",
    "cache_write_tokens",
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def parse_verifier_output(raw_output: str | None) -> tuple[str, dict[str, Any]]:
    if not raw_output:
        return "missing", {}
    try:
        return "complete", json.loads(raw_output)
    except json.JSONDecodeError:
        return "truncated", {}


def find_output_file(output_dir: Path, task_id: str, filename: str) -> Path | None:
    candidates = (
        output_dir / task_id / "mini_swe_agent" / filename,
        output_dir / task_id / "agent_output" / "logs" / "mini_swe_agent" / filename,
    )
    return next((path for path in candidates if path.exists()), None)


def trajectory_metadata(output_dir: Path, task_id: str) -> dict[str, Any]:
    trajectory_path = find_output_file(output_dir, task_id, "trajectory.json")
    summary_path = find_output_file(output_dir, task_id, "summary.json")
    trajectory = load_json(trajectory_path) if trajectory_path else {}
    agent_summary = load_json(summary_path) if summary_path else {}
    model_stats = trajectory.get("info", {}).get("model_stats", {})
    usage = {field: 0.0 for field in USAGE_FIELDS}
    business_action_recorded = False

    for message in trajectory.get("messages", []):
        for action in message.get("extra", {}).get("actions", []):
            command = str(action.get("command") or "")
            if "/app/tools/business_tool.py" in command and "record" in command:
                business_action_recorded = True
        response = message.get("extra", {}).get("response", {})
        response_usage = response.get("usage", {})
        usage["prompt_tokens"] += float(response_usage.get("prompt_tokens") or 0)
        usage["completion_tokens"] += float(
            response_usage.get("completion_tokens") or 0
        )
        prompt_details = response_usage.get("prompt_tokens_details") or {}
        usage["cached_tokens"] += float(
            prompt_details.get("cached_tokens")
            or response_usage.get("cache_read_input_tokens")
            or 0
        )
        usage["cache_write_tokens"] += float(
            prompt_details.get("cache_write_tokens")
            or prompt_details.get("cache_creation_tokens")
            or response_usage.get("cache_creation_input_tokens")
            or 0
        )

    usage["api_calls"] = float(model_stats.get("api_calls") or 0)
    usage["reported_cost_usd"] = float(model_stats.get("instance_cost") or 0)
    return {
        "usage": usage,
        "agent_outcome": agent_summary.get("outcome"),
        "agent_stop_reason": agent_summary.get("stop_reason"),
        "business_action_recorded": business_action_recorded,
        "trajectory_path": (
            f"valkyrie://{task_id}/mini_swe_agent/trajectory.json"
            if trajectory_path
            else None
        ),
    }


def add_usage(total: dict[str, float], usage: dict[str, float]) -> None:
    for field in (*USAGE_FIELDS, "api_calls", "reported_cost_usd"):
        total[field] += float(usage.get(field) or 0)


def iso_seconds(started_at: str, finished_at: str) -> float:
    return (datetime.fromisoformat(finished_at) - datetime.fromisoformat(started_at)).total_seconds()


def aggregate_model(
    model: str,
    runs: list[tuple[str, Path, Path]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    trial_scores: list[float] = []
    wall_clock_seconds: list[float] = []
    total_usage = {
        field: 0.0
        for field in (*USAGE_FIELDS, "api_calls", "reported_cost_usd")
    }

    for trial_index, (run_id, result_path, output_dir) in enumerate(runs, start=1):
        result = load_json(result_path)
        result_model = result["benchmark_arguments"]["contract"]["model"]
        if result_model != model:
            raise ValueError(
                f"{result_path} uses {result_model}, expected {model}"
            )
        if result.get("status") != "FINISHED":
            raise ValueError(f"{run_id} is not finished")

        wall_clock_seconds.append(
            iso_seconds(result["started_at"], result["finished_at"])
        )
        evaluations = result["evaluation_results"]
        scores = [float(evaluation["rewards"]["reward"]) for evaluation in evaluations.values()]
        trial_scores.append(statistics.mean(scores))

        for task_id, evaluation in evaluations.items():
            verifier_status, verifier = parse_verifier_output(
                evaluation.get("metadata", {}).get("verifier_output")
            )
            trajectory = trajectory_metadata(output_dir, task_id)
            add_usage(total_usage, trajectory["usage"])
            breakdown = evaluation.get("task_breakdown") or {}
            rows.append(
                {
                    "model": model,
                    "trial": f"trial-{trial_index}",
                    "run_id": run_id,
                    "task_id": task_id,
                    "score": float(evaluation["rewards"]["reward"]),
                    "passed": bool(
                        verifier.get(
                            "passed", float(evaluation["rewards"]["reward"]) == 1.0
                        )
                    ),
                    "verifier_metadata_status": verifier_status,
                    "failure_type": verifier.get("failure_type"),
                    "reason": verifier.get("reason"),
                    "forbidden_matches": verifier.get("forbidden_matches", []),
                    "components": verifier.get("components", {}),
                    "recorded_actions": verifier.get("recorded_actions", []),
                    "action_recorded": bool(
                        verifier.get("recorded_actions")
                        or trajectory["business_action_recorded"]
                    ),
                    "agent_exit_reason": evaluation.get("agent_caused_exit_reason"),
                    "agent_outcome": trajectory["agent_outcome"],
                    "agent_stop_reason": trajectory["agent_stop_reason"],
                    "agent_duration_seconds": breakdown.get("agent_run_duration"),
                    "sandbox_duration_seconds": breakdown.get("sandbox_run_duration"),
                    "usage": trajectory["usage"],
                    "trajectory_path": (
                        trajectory["trajectory_path"].replace(
                            "valkyrie://", f"valkyrie://{run_id}/"
                        )
                        if trajectory["trajectory_path"]
                        else None
                    ),
                }
            )

    per_task_scores: dict[str, list[float]] = defaultdict(list)
    failure_types: Counter[str] = Counter()
    for row in rows:
        per_task_scores[row["task_id"]].append(row["score"])
        failure_types[row["failure_type"] or "none"] += 1

    actionful_scores = [row["score"] for row in rows if row["action_recorded"]]
    per_task = {
        task_id: {
            "mean": statistics.mean(scores),
            "stddev": statistics.pstdev(scores),
            "scores": scores,
        }
        for task_id, scores in sorted(per_task_scores.items())
    }
    total_usage["reported_cost_usd"] = round(
        total_usage["reported_cost_usd"], 10
    )
    base_input_tokens = max(
        0.0,
        total_usage["prompt_tokens"]
        - total_usage["cached_tokens"]
        - total_usage["cache_write_tokens"],
    )
    return {
        "score_mean": statistics.mean(trial_scores),
        "score_stddev": statistics.pstdev(trial_scores),
        "trial_scores": trial_scores,
        "pass_rate": sum(row["score"] == 1.0 for row in rows) / len(rows),
        "blocking_violations": sum(bool(row["forbidden_matches"]) for row in rows),
        "no_action_failures": sum(
            row["verifier_metadata_status"] == "complete"
            and not row["action_recorded"]
            for row in rows
        ),
        "verifier_metadata_truncated": sum(
            row["verifier_metadata_status"] == "truncated" for row in rows
        ),
        "actionful_runs": len(actionful_scores),
        "actionful_score_mean": (
            statistics.mean(actionful_scores) if actionful_scores else 0.0
        ),
        "actionful_score_stddev": (
            statistics.pstdev(actionful_scores) if actionful_scores else 0.0
        ),
        "failure_types": dict(failure_types),
        "per_task": per_task,
        "rows": rows,
        "runs": [run_id for run_id, _, _ in runs],
        "base_input_tokens": base_input_tokens,
        "estimated_list_cost_usd": None,
        "usage": total_usage,
        "wall_clock_seconds": max(wall_clock_seconds),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    parser.add_argument(
        "--run",
        action="append",
        nargs=3,
        metavar=("RUN_ID", "RESULT_JSON", "OUTPUT_DIR"),
        required=True,
        help="Completed run ID, downloaded result JSON, and extracted output directory.",
    )
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    arguments = parser.parse_args()

    run_specs = [
        (run_id, Path(result_json).resolve(), Path(output_dir).resolve())
        for run_id, result_json, output_dir in arguments.run
    ]
    model_summary = aggregate_model(arguments.model, run_specs)
    summary = load_json(arguments.summary)
    summary["models"][arguments.model] = model_summary
    arguments.summary.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"Merged {arguments.model}: "
        f"{model_summary['score_mean'] * 100:.1f}% ± "
        f"{model_summary['score_stddev'] * 100:.1f} pp, "
        f"${model_summary['usage']['reported_cost_usd']:.2f} across "
        f"{len(model_summary['rows'])} attempts"
    )


if __name__ == "__main__":
    main()
