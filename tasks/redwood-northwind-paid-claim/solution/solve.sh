#!/bin/bash
set -euo pipefail
python3 /app/tools/business_tool.py record --action request_review --field 'subject_id="NW-PAID-Q4"' --field 'reviewer="Northwind Legal"' --field 'review_type="channel permission"'
python3 /app/tools/business_tool.py record --action update_record --field 'system="HubSpot"' --field 'subject_id="NW-PAID-Q4"' --field 'field="launch status"' --field 'value="pending permission"'
python3 /app/tools/business_tool.py record --action update_record --field 'subject_id="NW-PAID-Q4"' --field 'field="decision basis"' --field 'details="42% seven-day channel"'
python3 /app/tools/business_tool.py record --action draft_artifact --field 'subject_id="NW-PAID-Q4"' --field 'artifact_type="campaign draft"' --field 'details="25-35% observed in production results vary internal draft"' --field 'status="internal"'
