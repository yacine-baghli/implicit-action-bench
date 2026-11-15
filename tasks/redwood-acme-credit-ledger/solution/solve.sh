#!/bin/bash
set -euo pipefail
python3 /app/tools/business_tool.py record --action update_record --field 'system="billing"' --field 'subject_id="ACME-CREDIT-JAN"' --field 'field="credit amount"' --field 'value="1842.17"'
python3 /app/tools/business_tool.py record --action communicate --field 'recipient="Acme"' --field 'subject_id="INV-2026-02-ACME"' --field 'content="$1,842.17 next invoice unchanged separate review"' --field 'status="sent"'
python3 /app/tools/business_tool.py record --action update_record --field 'subject_id="INV-2026-02-ACME"' --field 'field="decision basis"' --field 'details="closed period 7.9% different window"'
python3 /app/tools/business_tool.py record --action create_work_item --field 'subject_id="ACME-LATER-WINDOW"' --field 'work_type="usage quantification"' --field 'owner="Billing"' --field 'details="Usage API later window separate approval"'
