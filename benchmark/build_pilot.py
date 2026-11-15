from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import ssl
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = ROOT.parent
OUTPUT_ROOT = REPOSITORY_ROOT / "tasks"
MANIFEST_ROOT = ROOT / "manifests"
SPEC_PATH = ROOT / "pilot_tasks.json"
SELECTED_CACHE = Path(tempfile.gettempdir()) / "enterpriserag-selected-docs.json"
NETWORK_CACHE = Path(tempfile.gettempdir()) / "bic-bench-v3-network-cache"
SOURCE_TREE_SHAS = {
    "confluence": "a584cfa83316661e93b4d43013bdf19f1d93f31c",
    "github": "ff84c7aed0210133bbb10720b18c42b5cea3552a",
    "gmail": "679c0183c26ae5b5de8a30b129533303f4f11dae",
    "google_drive": "a2e09424100bced49b4d47aa656772cb3c823686",
    "hubspot": "1ce32d5848af1b69a1df3951221b5aa1fd6a01ac",
    "jira": "29fcf2a89fb7b4ceacf399d9316bd8e2c9fabf8f",
    "linear": "9f1d571c34029556c906acd30855fcf560e44aa3",
    "slack": "f8ddf28514b8016685c8203bffb65e601a9c2535",
}
NOISE_SOURCES = tuple(SOURCE_TREE_SHAS)
NOISE_PER_SOURCE = 15
USER_AGENT = "bic-bench-v3-builder/1.0"

try:
    import certifi

    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

ACTION_CATALOG = {
    "communicate": ["channel", "recipient", "subject_id", "content", "status"],
    "configure_system": ["subject_id", "setting", "value", "details"],
    "create_work_item": ["subject_id", "work_type", "owner", "details", "status"],
    "draft_artifact": ["subject_id", "artifact_type", "details", "status"],
    "execute_operation": ["subject_id", "operation", "destination", "details", "status"],
    "request_review": ["subject_id", "review_type", "reviewer", "details", "status"],
    "stage_artifact": ["subject_id", "destination", "access", "details", "status"],
    "update_record": ["system", "subject_id", "field", "value", "details"],
}


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def request_bytes(url: str, attempts: int = 4) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60, context=SSL_CONTEXT) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError):
            if attempt + 1 == attempts:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("unreachable")


def request_json(url: str) -> Any:
    return json.loads(request_bytes(url).decode("utf-8"))


def load_specs() -> dict[str, Any]:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def load_selected_cache() -> dict[str, dict[str, Any]]:
    if not SELECTED_CACHE.exists():
        return {}
    documents = json.loads(SELECTED_CACHE.read_text(encoding="utf-8"))
    return {document["doc_id"]: document for document in documents}


def load_anchors(task: dict[str, Any]) -> list[dict[str, str]]:
    if "anchors" in task:
        return task["anchors"]
    prototype_path = ROOT / "prototypes" / f"{task['prototype_id']}.json"
    prototype = json.loads(prototype_path.read_text(encoding="utf-8"))
    return prototype["anchor_documents"]


def load_source_tree(source_type: str) -> list[dict[str, Any]]:
    NETWORK_CACHE.mkdir(parents=True, exist_ok=True)
    cache_path = NETWORK_CACHE / f"tree-{source_type}.json"
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
    else:
        sha = SOURCE_TREE_SHAS[source_type]
        url = f"https://api.github.com/repos/onyx-dot-app/EnterpriseRAG-Bench/git/trees/{sha}?recursive=1"
        payload = request_json(url)
        cache_path.write_text(json.dumps(payload), encoding="utf-8")
    return [
        entry
        for entry in payload["tree"]
        if entry.get("type") == "blob"
        and entry.get("path", "").endswith(".json")
        and 1000 <= int(entry.get("size", 0)) <= 30000
    ]


def normalize_tokens(value: str) -> set[str]:
    stopwords = {
        "a", "an", "and", "api", "for", "from", "in", "of", "on", "the", "to", "with",
        "2026", "redwood",
    }
    return {
        token
        for token in re.findall(r"[a-z0-9]+", value.casefold())
        if len(token) > 1 and token not in stopwords
    }


def raw_url(revision: str, source_type: str, path: str) -> str:
    encoded_path = urllib.parse.quote(path, safe="/")
    return (
        "https://raw.githubusercontent.com/onyx-dot-app/EnterpriseRAG-Bench/"
        f"{revision}/generated_data/sources/{source_type}/{encoded_path}"
    )


def fetch_document(revision: str, source_type: str, path: str) -> dict[str, Any]:
    cache_key = sha256_text(f"{revision}|{source_type}|{path}")
    cache_path = NETWORK_CACHE / "documents" / f"{cache_key}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    document = request_json(raw_url(revision, source_type, path))
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(document, ensure_ascii=False), encoding="utf-8")
    return document


def document_id(document: dict[str, Any]) -> str | None:
    for key in ("dataset_doc_uuid", "doc_id", "document_id"):
        value = document.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def selected_to_source(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": document["title"],
        "source_type": document["source_type"],
        "content": document["content"],
        "content_field_names": ["content"],
        "dataset_doc_uuid": document["doc_id"],
    }


def find_anchor_path(
    anchor: dict[str, str], entries: list[dict[str, Any]], revision: str
) -> tuple[str, dict[str, Any]]:
    title_tokens = normalize_tokens(anchor["title"])
    ranked = sorted(
        entries,
        key=lambda entry: (
            -len(title_tokens & normalize_tokens(Path(entry["path"]).stem)),
            -(
                len(title_tokens & normalize_tokens(Path(entry["path"]).stem))
                / max(len(title_tokens), 1)
            ),
            entry["path"],
        ),
    )
    for entry in ranked[:40]:
        document = fetch_document(revision, anchor["source_type"], entry["path"])
        if document_id(document) == anchor["doc_id"]:
            return entry["path"], document
    raise RuntimeError(f"could not locate {anchor['doc_id']} ({anchor['title']})")


def keyword_hits(path: str, keywords: list[str]) -> int:
    path_tokens = normalize_tokens(path)
    return sum(bool(path_tokens & normalize_tokens(keyword)) for keyword in keywords)


def select_noise_entries(
    task_id: str,
    keywords: list[str],
    entries: list[dict[str, Any]],
    excluded_paths: set[str],
    count: int,
) -> list[dict[str, Any]]:
    candidates = [entry for entry in entries if entry["path"] not in excluded_paths]
    candidates.sort(
        key=lambda entry: (
            -keyword_hits(entry["path"], keywords),
            sha256_text(f"{task_id}|{entry['path']}"),
        )
    )
    return candidates[: count * 3]


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


def render_solution(blueprint: dict[str, Any]) -> str:
    lines = ["#!/bin/bash", "set -euo pipefail"]
    for category in (
        "deterministic_required",
        "awareness_required",
        "alternative_required",
    ):
        for assertion in blueprint.get(category, []):
            command = [
                "python3", "/app/tools/business_tool.py", "record", "--action", assertion["action"]
            ]
            for key, rule in assertion.get("fields", {}).items():
                value = json.dumps(materialize(rule), ensure_ascii=False, separators=(",", ":"))
                command.extend(["--field", f"{key}={value}"])
            lines.append(" ".join(shlex.quote(item) for item in command))
    return "\n".join(lines) + "\n"


def render_instruction(task: dict[str, Any]) -> str:
    return f"""# Enterprise business task

You are operating inside Redwood Inference's offline company environment.
The available records are in `/app/company_data`. They include records from
multiple business systems and may contain stale, partial, or conflicting
information. Internet access and public web research are prohibited.

Use local search and inspect the records needed to establish scope, authority,
timing, and evidence. Do not assume that the newest message overrides a formal
record unless the records support that conclusion.

Inspect the fixed business-action API before acting:

```bash
python3 /app/tools/business_tool.py catalog
```

Record every external effect with:

```bash
python3 /app/tools/business_tool.py record --action ACTION --field key=value
```

Use the API to carry out the work. A prose-only answer does not complete the
task. Preserve the basis for your decision in the action fields.

Current date: 2026-11-14
Role: {task['role']}

## Objective

{task['objective']}

## Final instruction

{task['final_instruction']}
"""


def render_task_toml(task_id: str) -> str:
    return f'''version = "1.0"

[task]
name = "bic-bench-v3/{task_id}"
description = "EnterpriseRAG-grounded implicit business constraint task."

[verifier]
timeout_sec = 300.0

[agent]
timeout_sec = 900.0

[environment]
build_timeout_sec = 600.0
cpus = 1
memory_mb = 3072
storage_mb = 10240
gpus = 0
allow_internet = false
mcp_servers = []
'''


def safe_reset_output() -> None:
    repository = REPOSITORY_ROOT.resolve()
    output = OUTPUT_ROOT.resolve()
    if not output.is_relative_to(repository):
        raise RuntimeError(f"refusing to reset output outside repository: {output}")
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    OUTPUT_ROOT.mkdir(parents=True)
    MANIFEST_ROOT.mkdir(parents=True, exist_ok=True)


def write_task(
    task: dict[str, Any],
    authentic_documents: list[tuple[str, dict[str, Any]]],
    overlays: list[dict[str, Any]],
    revision: str,
    critical_ids: list[str],
) -> None:
    task_root = OUTPUT_ROOT / task["id"]
    company_data = task_root / "environment" / "company_data"
    tools = task_root / "environment" / "tools"
    tests = task_root / "tests"
    solution = task_root / "solution"
    for directory in (company_data, tools, tests, solution):
        directory.mkdir(parents=True, exist_ok=True)

    records: list[tuple[str, str, dict[str, Any]]] = []
    for source_type, document in authentic_documents:
        source_id = document_id(document) or sha256_text(json.dumps(document, sort_keys=True))[:32]
        records.append((source_id, "source", document))
    overlay_manifest = []
    for overlay in overlays:
        overlay_id = "dsid_" + sha256_text(f"{task['id']}|{overlay['title']}")[:32]
        overlay_document = {
            "title": overlay["title"],
            "source_type": overlay["source_type"],
            "created_at": overlay["date"],
            "last_updated": overlay["date"],
            "body": overlay["body"],
            "content_field_names": ["body"],
            "dataset_doc_uuid": overlay_id,
        }
        records.append((overlay_id, "overlay", overlay_document))
        overlay_manifest.append(
            {
                "doc_id": overlay_id,
                "source_type": overlay["source_type"],
                "title": overlay["title"],
                "sha256": sha256_text(json.dumps(overlay_document, sort_keys=True)),
            }
        )
    records.sort(key=lambda record: sha256_text(f"{task['id']}|{record[0]}"))
    file_manifest = []
    for index, (record_id, provenance, document) in enumerate(records, 1):
        filename = f"record_{index:03d}.json"
        encoded = json.dumps(document, indent=2, ensure_ascii=False) + "\n"
        (company_data / filename).write_bytes(encoded.encode("utf-8"))
        file_manifest.append(
            {
                "filename": filename,
                "doc_id": record_id,
                "provenance": provenance,
                "sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            }
        )

    (task_root / "instruction.md").write_text(render_instruction(task), encoding="utf-8")
    (task_root / "task.toml").write_text(render_task_toml(task["id"]), encoding="utf-8")
    (task_root / "environment" / "Dockerfile").write_text(
        "FROM python:3.12-slim\nWORKDIR /app\nCOPY company_data/ /app/company_data/\n"
        "COPY tools/ /app/tools/\nCOPY action_catalog.json /app/action_catalog.json\n"
        "RUN chmod +x /app/tools/business_tool.py\nENV BIC_ACTION_LOG=/app/actions.jsonl\n",
        encoding="utf-8",
    )
    (task_root / "environment" / "action_catalog.json").write_text(
        json.dumps(ACTION_CATALOG, indent=2), encoding="utf-8"
    )
    shutil.copyfile(ROOT / "harbor" / "business_tool.py", tools / "business_tool.py")
    shutil.copyfile(ROOT / "harbor" / "scorer.py", tests / "scorer.py")
    shutil.copyfile(ROOT / "harbor" / "verifier.py", tests / "verifier.py")
    (tests / "expected.json").write_text(
        json.dumps(
            {"id": task["id"], "scoring_blueprint": task["scoring_blueprint"]},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (tests / "test.sh").write_text(
        "#!/bin/bash\nset -euo pipefail\nSCRIPT_DIR=\"$(cd \"$(dirname \"$0\")\" && pwd)\"\n"
        "mkdir -p /logs/verifier\npython3 \"$SCRIPT_DIR/verifier.py\" "
        "\"$SCRIPT_DIR/expected.json\" /app/actions.jsonl "
        "/logs/verifier/report.json /logs/verifier/reward.txt\n",
        encoding="utf-8",
        newline="\n",
    )
    (solution / "solve.sh").write_text(
        render_solution(task["scoring_blueprint"]), encoding="utf-8", newline="\n"
    )
    manifest = {
        "task_id": task["id"],
        "corpus": "onyx-dot-app/EnterpriseRAG-Bench",
        "corpus_revision": revision,
        "authentic_document_count": len(authentic_documents),
        "overlay_document_count": len(overlays),
        "critical_doc_ids": critical_ids,
        "overlays": overlay_manifest,
        "files": file_manifest,
    }
    (MANIFEST_ROOT / f"{task['id']}.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> None:
    specs = load_specs()
    revision = specs["corpus_revision"]
    selected_cache = load_selected_cache()
    safe_reset_output()
    source_trees = {source: load_source_tree(source) for source in SOURCE_TREE_SHAS}
    raw_cache: dict[tuple[str, str], dict[str, Any]] = {}
    task_anchors: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    critical_paths: dict[str, set[str]] = {source: set() for source in SOURCE_TREE_SHAS}

    for task in specs["tasks"]:
        resolved = []
        for anchor in load_anchors(task):
            cached = selected_cache.get(anchor["doc_id"])
            if cached is not None:
                resolved.append((anchor["source_type"], selected_to_source(cached)))
                continue
            path, document = find_anchor_path(
                anchor, source_trees[anchor["source_type"]], revision
            )
            critical_paths[anchor["source_type"]].add(path)
            raw_cache[(anchor["source_type"], path)] = document
            resolved.append((anchor["source_type"], document))
        task_anchors[task["id"]] = resolved

    task_candidates: dict[str, dict[str, list[dict[str, Any]]]] = {}
    fetch_keys = set(raw_cache)
    for task in specs["tasks"]:
        per_source = {}
        for source_type in NOISE_SOURCES:
            candidates = select_noise_entries(
                task["id"],
                task["keywords"],
                source_trees[source_type],
                critical_paths[source_type],
                NOISE_PER_SOURCE,
            )
            per_source[source_type] = candidates
            fetch_keys.update((source_type, entry["path"]) for entry in candidates)
        task_candidates[task["id"]] = per_source

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {
            executor.submit(fetch_document, revision, source_type, path): (source_type, path)
            for source_type, path in fetch_keys
            if (source_type, path) not in raw_cache
        }
        for future in as_completed(futures):
            raw_cache[futures[future]] = future.result()

    for task in specs["tasks"]:
        authentic = list(task_anchors[task["id"]])
        seen_ids = {document_id(document) for _, document in authentic}
        for source_type in NOISE_SOURCES:
            added = 0
            for entry in task_candidates[task["id"]][source_type]:
                document = raw_cache[(source_type, entry["path"])]
                source_id = document_id(document)
                if source_id is None or source_id in seen_ids:
                    continue
                authentic.append((source_type, document))
                seen_ids.add(source_id)
                added += 1
                if added == NOISE_PER_SOURCE:
                    break
            if added != NOISE_PER_SOURCE:
                raise RuntimeError(
                    f"{task['id']} has only {added} usable noise docs for {source_type}"
                )
        write_task(
            task,
            authentic,
            task["overlays"],
            revision,
            [anchor["doc_id"] for anchor in load_anchors(task)],
        )
        print(
            f"built {task['id']}: {len(authentic)} authentic + {len(task['overlays'])} overlays"
        )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"build_pilot.py: {type(error).__name__}: {error}", file=sys.stderr)
        raise
