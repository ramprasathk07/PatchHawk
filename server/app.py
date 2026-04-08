"""
PatchHawk OpenEnv server entry point.

This file satisfies the ``openenv validate`` requirement for a
``server/app.py`` module that exposes a ``main()`` function.

Run directly:
    python server/app.py
    python server/app.py --port 7860

Or via the project script:
    server              (after pip install -e .)

Or via openenv serve (Docker / deployment):
    openenv serve --env patchhawk.agent.environment:PatchHawkEnv --port 7860
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path when run directly
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from openenv.core import create_app

from patchhawk.agent.environment import PatchHawkEnv
from patchhawk.env_models import PatchHawkAction, PatchHawkObservation
from fastapi.responses import HTMLResponse, StreamingResponse
import httpx
from starlette.requests import Request
from starlette.background import BackgroundTask


def _env_factory() -> PatchHawkEnv:
    """Factory callable for create_app — returns a fresh PatchHawkEnv instance."""
    scenarios_path = os.getenv("PATCHHAWK_SCENARIOS", "patchhawk/data/scenarios.json")
    return PatchHawkEnv(scenarios_path=scenarios_path, use_docker=False)


def create_openenv_app():
    """Create the OpenEnv FastAPI application."""
    return create_app(
        _env_factory,
        PatchHawkAction,
        PatchHawkObservation,
        env_name="PatchHawk",
    )


app = create_openenv_app()

# ── Streamlit Proxy Configuration ─────────────────────────────────────
STREAMLIT_URL = "http://localhost:8501"

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
async def proxy_streamlit(request: Request, path: str):
    """
    Proxies all requests not handled by OpenEnv routes to the local Streamlit server.
    This ensures the Streamlit Dashboard is the primary UI on port 7860.
    """
    # Skip proxying for OpenEnv specific routes so the grader still works
    openenv_routes = ["reset", "step", "docs", "openapi.json", "web", "assets"]
    if any(path.startswith(r) for r in openenv_routes) or path == "":
        if path == "":
             # Redirect root to Streamlit
             pass
        else:
            # Let FastAPI handle it
            return

    client = httpx.AsyncClient(base_url=STREAMLIT_URL)
    url = httpx.URL(path=request.url.path, query=request.url.query.encode("utf-8"))
    
    # Filter out headers that might cause issues with the proxy
    headers = {k: v for k, v in request.headers.items() if k.lower() not in ["host", "connection"]}
    
    # Handle the request body
    body = await request.body()
    
    # Forward the request to Streamlit
    rp_resp = await client.request(
        method=request.method,
        url=url,
        headers=headers,
        content=body,
        follow_redirects=True,
    )

    return StreamingResponse(
        rp_resp.aiter_raw(),
        status_code=rp_resp.status_code,
        headers=dict(rp_resp.headers),
        background=BackgroundTask(client.aclose)
    )

@app.get("/", response_class=HTMLResponse)
async def root_redirect(request: Request):
    """Force the root to proxy to Streamlit."""
    return await proxy_streamlit(request, "")


def main(port: int | None = None) -> None:
    """Start the PatchHawk OpenEnv server."""
    import uvicorn

    if port is None:
        # Parse --port from CLI args
        args = sys.argv[1:]
        if "--port" in args:
            idx = args.index("--port")
            if idx + 1 < len(args):
                port = int(args[idx + 1])
        if port is None:
            port = int(os.getenv("PORT", "7860"))

    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
