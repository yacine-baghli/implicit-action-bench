from __future__ import annotations

import argparse
import importlib.util
import json
import statistics
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent


def load_scorer():
    path = ROOT / "harbor" / "scorer.py"
    spec = importlib.util.spec_from_file_location("bic_v3_scorer", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("scorer loader unavailable")
    spec.loader.exec_module(module)
    return module


def load_blueprints() -> dict[str, dict[str, Any]]:
    specs = json.loads((ROOT / "pilot_tasks.json").read_text(encoding="utf-8"))
    return {task["id"]: task["scoring_blueprint"] for task in specs["tasks"]}


def load_actions(evaluation: dict[str, Any]) -> list[dict[str, Any]]:
    output = evaluation["metadata"]["verifier_output"]
    return json.loads(output)["recorded_actions"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="+", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    scorer = load_scorer()
    blueprints = load_blueprints()
    rows = []
    for trial, result_path in enumerate(args.results, 1):
        result = json.loads(result_path.read_text(encoding="utf-8-sig"))
        for task_id, evaluation in sorted(result["evaluation_results"].items()):
            rescored = scorer.score_actions(
                {"id": task_id, "scoring_blueprint": blueprints[task_id]},
                load_actions(evaluation),
            )
            rows.append(
                {
                    "trial": trial,
                    "task_id": task_id,
                    "reward": rescored["reward"],
                    "failure_type": rescored["failure_type"],
                    "forbidden": bool(rescored["forbidden_matches"]),
                    "components": {
                        name: component["score"]
                        for name, component in rescored["components"].items()
                    },
                }
            )
    rewards = [row["reward"] for row in rows]
    summary = {
        "mean": statistics.fmean(rewards),
        "stddev": statistics.pstdev(rewards),
        "n": len(rewards),
        "rows": rows,
    }
    for row in rows:
        print(
            f"t{row['trial']} {row['task_id']}: {row['reward']:.3f} "
            f"forbidden={row['forbidden']} components={row['components']}"
        )
    print(f"mean={summary['mean']:.4f} stddev={summary['stddev']:.4f} n={summary['n']}")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
