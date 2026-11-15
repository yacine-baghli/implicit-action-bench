#!/bin/bash
set -euo pipefail
python3 /app/tools/business_tool.py record --action create_work_item --field 'subject_id="PROXIMA-BURST-30"' --field 'work_type="fresh change request"' --field 'owner="SRE Platform"' --field 'details="region route duration canary rollback"'
python3 /app/tools/business_tool.py record --action update_record --field 'system="Jira"' --field 'subject_id="PROXIMA-BURST-30"' --field 'field="implementation status"' --field 'value="pending review"'
python3 /app/tools/business_tool.py record --action update_record --field 'subject_id="PROXIMA-BURST-30"' --field 'field="decision basis"' --field 'details="expired 14 days us-east chat embeddings"'
python3 /app/tools/business_tool.py record --action communicate --field 'recipient="Proxima"' --field 'subject_id="PROXIMA-BURST-30"' --field 'content="review Dedicated capacity not yet enabled"' --field 'status="sent"'
