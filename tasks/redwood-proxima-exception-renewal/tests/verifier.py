#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        print("usage: verifier.py EXPECTED ACTIONS REPORT REWARD", file=sys.stderr)
        return 2
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from scorer import score_files

    result = score_files(Path(sys.argv[1]), Path(sys.argv[2]))
    report_path = Path(sys.argv[3])
    reward_path = Path(sys.argv[4])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    reward_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    reward_path.write_text(str(result["reward"]), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
