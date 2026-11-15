#!/bin/bash
set -euo pipefail
python3 /app/tools/business_tool.py record --action update_record --field 'system="Linear"' --field 'subject_id="ARGON-70B-LAUNCH"' --field 'field="launch status"' --field 'value="blocked"'
python3 /app/tools/business_tool.py record --action request_review --field 'subject_id="ARGON-70B-LAUNCH"' --field 'reviewer="Legal Security"' --field 'review_type="license restriction"'
python3 /app/tools/business_tool.py record --action update_record --field 'subject_id="ARGON-70B-LAUNCH"' --field 'field="decision basis"' --field 'details="latency license safety EU quant rollback"'
python3 /app/tools/business_tool.py record --action configure_system --field 'subject_id="ARGON-70B-LAUNCH"' --field 'setting="deployment mode"' --field 'value="internal shadow"' --field 'details="complete missing gates"'
