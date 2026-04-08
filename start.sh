#!/bin/bash

API_PORT="${API_PORT:-8000}"
PORT="${PORT:-7860}"

# Start FastAPI on API_PORT
echo "Starting OpenEnv API server on port ${API_PORT}..."
uvicorn server.app:app --host 0.0.0.0 --port "${API_PORT}" &

# Start the Streamlit Dashboard (User UI) in the background with Proxy-friendly settings
echo "Starting Streamlit Dashboard on port 8501..."
streamlit run patchhawk/app/dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --server.headless true \
    --browser.gatherUsageStats false &

# Start Nginx in foreground on PORT
echo "Starting Nginx reverse proxy on ${PORT}..."
envsubst '${PORT}' < /etc/nginx/nginx.conf > /tmp/nginx.conf && nginx -c /tmp/nginx.conf -g "daemon off;"
