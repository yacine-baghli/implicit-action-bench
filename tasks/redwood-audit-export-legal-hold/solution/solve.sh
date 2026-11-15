#!/bin/bash
set -euo pipefail
python3 /app/tools/business_tool.py record --action create_work_item --field 'subject_id="CONCORDIA-AUDIT-15M"' --field 'work_type="legal hold"' --field 'owner="Legal Compliance"' --field 'details="hold ID"'
python3 /app/tools/business_tool.py record --action update_record --field 'system="support"' --field 'subject_id="CONCORDIA-AUDIT-15M"' --field 'field="export status"' --field 'value="pending legal hold"'
python3 /app/tools/business_tool.py record --action update_record --field 'subject_id="CONCORDIA-AUDIT-15M"' --field 'field="decision basis"' --field 'details="super-admin does not bypass retention legal hold ID"'
python3 /app/tools/business_tool.py record --action draft_artifact --field 'subject_id="CONCORDIA-AUDIT-15M"' --field 'artifact_type="available-range manifest"' --field 'details="within retention separate older range pending hold"' --field 'status="prepared"'
