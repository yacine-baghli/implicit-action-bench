#!/bin/bash
set -euo pipefail
python3 /app/tools/business_tool.py record --action update_record --field 'system="SLO dashboard"' --field 'subject_id="HELIOS-SLO-118"' --field 'field="historical annotation"' --field 'value="pre-fix streaming uncertain"'
python3 /app/tools/business_tool.py record --action create_work_item --field 'subject_id="HELIOS-SLO-118"' --field 'work_type="SLO validation"' --field 'owner="SRE"' --field 'details="finalized completion tokens impact window tier exclusions"'
python3 /app/tools/business_tool.py record --action update_record --field 'subject_id="HELIOS-SLO-118"' --field 'field="decision basis"' --field 'details="double-count masked no automatic backfill no pre-approval"'
python3 /app/tools/business_tool.py record --action request_review --field 'subject_id="HELIOS-SLO-118"' --field 'reviewer="Product Finance"' --field 'review_type="SLA entitlement"' --field 'details="after SRE validation"'
