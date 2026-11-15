#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


CATALOG_PATH = Path("/app/action_catalog.json")
LOG_PATH = Path(os.environ.get("BIC_ACTION_LOG", "/app/actions.jsonl"))


def load_catalog() -> dict[str, list[str]]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def parse_value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def parse_fields(items: list[str]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"field must use key=value syntax: {item}")
        key, value = item.split("=", 1)
        if not key:
            raise ValueError("field key cannot be empty")
        fields[key] = parse_value(value)
    return fields


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect and record offline simulated business actions."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("catalog", help="Show the fixed action signatures.")
    record = subparsers.add_parser("record", help="Record one simulated action.")
    record.add_argument("--action", required=True)
    record.add_argument("--field", action="append", default=[])
    return parser


def main() -> None:
    args = build_parser().parse_args()
    catalog = load_catalog()
    if args.command == "catalog":
        for action, fields in catalog.items():
            print(f"{action}({', '.join(fields)})")
        return

    if args.action not in catalog:
        raise SystemExit(f"unknown action: {args.action}; run catalog first")
    record = {
        "action": args.action,
        "fields": parse_fields(args.field),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as log_file:
        log_file.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(json.dumps({"recorded": record}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
