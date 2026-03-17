#!/bin/bash
# Opalstack startup script for Streamlit app
# PORT is set by Opalstack in the Custom App configuration
cd "$(dirname "$0")"
source venv/bin/activate
exec streamlit run app.py \
  --server.port "$PORT" \
  --server.address 127.0.0.1 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false
