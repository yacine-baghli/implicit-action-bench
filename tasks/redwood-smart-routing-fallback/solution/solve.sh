#!/bin/bash
set -euo pipefail
python3 /app/tools/business_tool.py record --action create_work_item --field 'subject_id="ATLAS-503-FALLBACK"' --field 'work_type="gateway admission investigation"' --field 'owner="Gateway"' --field 'details="GATEWAY_ADMISSION_OVERLOAD threshold capacity"'
python3 /app/tools/business_tool.py record --action update_record --field 'system="support"' --field 'subject_id="ATLAS-503-FALLBACK"' --field 'field="root cause"' --field 'value="gateway admission before routing"'
python3 /app/tools/business_tool.py record --action update_record --field 'subject_id="ATLAS-503-FALLBACK"' --field 'field="decision basis"' --field 'details="no router decision ID breaker open same-region contract"'
python3 /app/tools/business_tool.py record --action communicate --field 'recipient="Atlas"' --field 'subject_id="ATLAS-503-FALLBACK"' --field 'content="admission before routing bounded fallback retry"' --field 'status="sent"'
