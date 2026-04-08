#!/bin/bash
# Start the OpenEnv API server (Hackathon Compliance)
echo "Starting OpenEnv API server on port 7860..."
uvicorn server.app:app --host 0.0.0.0 --port 7860 &

# Start the Streamlit Dashboard (User UI)
echo "Starting Streamlit Dashboard on port 8501..."
streamlit run patchhawk/app/dashboard.py --server.port 8501 --server.address 0.0.0.0
