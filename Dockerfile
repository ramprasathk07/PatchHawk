FROM python:3.11-slim

# System dependencies (docker.io for Docker-in-Docker sandbox)
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl docker.io \
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

# Expose the OpenEnv server port
EXPOSE 7860

# Launch the OpenEnv HTTP server
CMD ["openenv", "serve", "--env", "patchhawk.agent.environment:PatchHawkEnv", "--port", "7860"]
