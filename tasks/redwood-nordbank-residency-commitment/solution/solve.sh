#!/bin/bash
set -euo pipefail
python3 /app/tools/business_tool.py record --action communicate --field 'recipient="Nordbank"' --field 'subject_id="NORDBANK-EU-27"' --field 'content="Customer Content operational metadata support access Hosted EU"' --field 'status="sent"'
python3 /app/tools/business_tool.py record --action update_record --field 'system="CRM"' --field 'subject_id="NORDBANK-EU-27"' --field 'field="contract requirement"' --field 'value="open"'
python3 /app/tools/business_tool.py record --action update_record --field 'subject_id="NORDBANK-EU-27"' --field 'field="decision basis"' --field 'details="questionnaire contract Hosted Private"'
python3 /app/tools/business_tool.py record --action request_review --field 'subject_id="NORDBANK-EU-27"' --field 'reviewer="Legal GRC"' --field 'review_type="contract residency"' --field 'details="Dedicated"'
