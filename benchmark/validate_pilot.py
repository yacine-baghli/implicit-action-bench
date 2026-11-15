from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parent
TASK_ROOT = REPOSITORY_ROOT / "tasks"
MANIFEST_ROOT = ROOT / "manifests"
EXPECTED_TASKS = 8
REQUIRED_COMPONENTS = (
    "deterministic_required",
    "awareness_required",
    "alternative_required",
)


def materialize(rule: Any) -> Any:
    if not isinstance(rule, dict):
        return rule
    if "contains_all" in rule:
        return " ".join(str(value) for value in rule["contains_all"])
    for key in ("equals", "contains", "contains_any", "at_most"):
        if key in rule:
            value = rule[key]
            return value[0] if isinstance(value, list) and value else value
    return "documented"


def load_scorer():
    path = ROOT / "harbor" / "scorer.py"
    spec = importlib.util.spec_from_file_location("bic_v3_scorer", path)
    module = importlib.util.module_from_spec(spec)
    if spec.loader is None:
        raise RuntimeError("scorer loader unavailable")
    spec.loader.exec_module(module)
    return module


def action_for(assertion: dict[str, Any]) -> dict[str, Any]:
    return {
        "action": assertion["action"],
        "fields": {
            key: materialize(rule)
            for key, rule in assertion.get("fields", {}).items()
        },
    }


def validate_task(task_root: Path, scorer) -> list[str]:
    errors = []
    task_id = task_root.name
    task_toml = (task_root / "task.toml").read_text(encoding="utf-8")
    if "allow_internet = false" not in task_toml or "allow_internet = true" in task_toml:
        errors.append(f"{task_id}: internet is not disabled")
    manifest = json.loads((MANIFEST_ROOT / f"{task_id}.json").read_text(encoding="utf-8"))
    if manifest["authentic_document_count"] < 120:
        errors.append(f"{task_id}: fewer than 120 authentic documents")
    if not 2 <= manifest["overlay_document_count"] <= 4:
        errors.append(f"{task_id}: overlay count outside 2-4")
    company_data = task_root / "environment" / "company_data"
    if len(list(company_data.glob("record_*.json"))) != len(manifest["files"]):
        errors.append(f"{task_id}: file count differs from manifest")
    visible_ids = set()
    for record in manifest["files"]:
        path = company_data / record["filename"]
        encoded = path.read_bytes()
        if hashlib.sha256(encoded).hexdigest() != record["sha256"]:
            errors.append(f"{task_id}: hash mismatch for {record['filename']}")
        document = json.loads(encoded)
        visible_ids.add(document.get("dataset_doc_uuid"))
        if "provenance" in document:
            errors.append(f"{task_id}: provenance leaked into {record['filename']}")
    if not set(manifest["critical_doc_ids"]).issubset(visible_ids):
        errors.append(f"{task_id}: critical document missing")

    expected = json.loads((task_root / "tests" / "expected.json").read_text(encoding="utf-8"))
    blueprint = expected["scoring_blueprint"]
    if not blueprint.get("forbidden"):
        errors.append(f"{task_id}: no blocking assertion")
    for component in REQUIRED_COMPONENTS:
        if not blueprint.get(component):
            errors.append(f"{task_id}: empty {component}")
    oracle_actions = [
        action_for(assertion)
        for component in REQUIRED_COMPONENTS
        for assertion in blueprint[component]
    ]
    oracle = scorer.score_actions(expected, oracle_actions)
    if oracle["reward"] != 1.0:
        component_scores = {
            name: component["score"] for name, component in oracle["components"].items()
        }
        errors.append(
            f"{task_id}: oracle reward is {oracle['reward']} ({component_scores})"
        )
    forbidden = scorer.score_actions(expected, [action_for(blueprint["forbidden"][0])])
    if forbidden["reward"] != 0.0 or forbidden["failure_type"] != "forbidden_action":
        errors.append(f"{task_id}: blocking gate failed")
    return errors


def main() -> int:
    task_roots = sorted(path.parent for path in TASK_ROOT.glob("*/task.toml"))
    if len(task_roots) != EXPECTED_TASKS:
        print(f"expected {EXPECTED_TASKS} tasks, found {len(task_roots)}", file=sys.stderr)
        return 1
    scorer = load_scorer()
    errors = [error for task_root in task_roots for error in validate_task(task_root, scorer)]
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    authentic = sum(
        json.loads((MANIFEST_ROOT / f"{task_root.name}.json").read_text(encoding="utf-8"))[
            "authentic_document_count"
        ]
        for task_root in task_roots
    )
    print(f"validated {len(task_roots)} tasks with {authentic} authentic document placements")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
