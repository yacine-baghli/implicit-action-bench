FROM python:3.12-slim
WORKDIR /app
COPY company_data/ /app/company_data/
COPY tools/ /app/tools/
COPY action_catalog.json /app/action_catalog.json
RUN chmod +x /app/tools/business_tool.py
ENV BIC_ACTION_LOG=/app/actions.jsonl
