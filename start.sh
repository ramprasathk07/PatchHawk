#!/bin/bash
# Start the OpenEnv API server (Hackathon Compliance)
echo "Starting OpenEnv API server on port 7860..."
uvicorn server.app:app --host 0.0.0.0 --port 7860 &

# Start the Streamlit Dashboard (User UI) in the background with Proxy-friendly settings
echo "Starting Streamlit Dashboard on port 8501..."
streamlit run patchhawk/app/dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.enableCORS false \
    --server.enableXsrfProtection false \
    --server.headless true \
    --browser.gatherUsageStats false &

# Start the OpenEnv API server (Hackathon Compliance) on Port 7860
# This server now PROXIES all UI requests to Streamlit on 8501
echo "Starting OpenEnv API server on port 7860..."
uvicorn server.app:app --host 0.0.0.0 --port 7860
