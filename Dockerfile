FROM python:3.11-slim

# System dependencies (docker.io for Docker-in-Docker sandbox, nginx for proxying)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl docker.io nginx gettext-base \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY patchhawk/ patchhawk/
COPY server/ server/
COPY openenv.yaml .
COPY pyproject.toml .
COPY inference.py .
COPY config.yaml .
COPY nginx.conf /etc/nginx/nginx.conf

# Copy and configure the startup script
COPY start.sh .
RUN chmod +x start.sh

# Expose both the OpenEnv API port and Streamlit port
EXPOSE 7860
EXPOSE 8501

# Launch both servers
CMD ["./start.sh"]
