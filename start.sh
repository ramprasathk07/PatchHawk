#!/bin/bash

API_PORT="${API_PORT:-8000}"
PORT="${PORT:-7860}"

# Start FastAPI on API_PORT
echo "[SYSTEM] Starting OpenEnv API server on port ${API_PORT}..."
uvicorn server.app:app --host 0.0.0.0 --port "${API_PORT}" 2>&1 | sed 's/^/[FASTAPI] /' &

# Start the Streamlit Dashboard (User UI) in the background with Proxy-friendly settings
echo "[SYSTEM] Starting Streamlit Dashboard on port 8501..."
streamlit run patchhawk/app/dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --server.headless true \
    --browser.gatherUsageStats false 2>&1 | sed 's/^/[STREAMLIT] /' &

# Start Nginx in foreground on PORT
echo "[SYSTEM] Starting Nginx reverse proxy on ${PORT}..."
envsubst '${PORT}' < /etc/nginx/nginx.conf > /tmp/nginx.conf

# Validate Nginx config
nginx -t -c /tmp/nginx.conf
if [ $? -ne 0 ]; then
    echo "[ERROR] Nginx configuration validation failed!"
    exit 1
fi

exec nginx -c /tmp/nginx.conf -g "daemon off;"
