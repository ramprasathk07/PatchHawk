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
from fastapi.responses import HTMLResponse


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

@app.get("/", response_class=HTMLResponse)
def root_dashboard():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>PatchHawk | Autonomous DevSecOps SOC</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; margin: 0; }
            .container { background: #161b22; padding: 40px; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 10px 30px rgba(0,0,0,0.5); text-align: center; max-width: 600px; }
            h1 { color: #58a6ff; margin-bottom: 10px; }
            p { font-size: 1.1em; color: #8b949e; line-height: 1.6; }
            .status { display: inline-block; padding: 5px 15px; border-radius: 20px; background: #238636; color: white; font-weight: bold; margin: 20px 0; }
            .links { display: flex; gap: 10px; justify-content: center; margin-top: 30px; }
            .btn { text-decoration: none; padding: 12px 25px; border-radius: 6px; font-weight: bold; transition: 0.3s; }
            .btn-blue { background: #1f6feb; color: white; }
            .btn-blue:hover { background: #388bfd; }
            .btn-outline { border: 1px solid #30363d; color: #58a6ff; }
            .btn-outline:hover { background: #30363d; }
            .badge { background: #30363d; padding: 4px 10px; border-radius: 4px; font-family: monospace; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🦅 PatchHawk SOC</h1>
            <p>Autonomous Supply-Chain Vulnerability & Patching Agent</p>
            <div class="status">● ENVIRONMENT LIVE</div>
            <p>The OpenEnv API Spec is running correctly at <span class="badge">port: 7860</span>.</p>
            
            <div class="links">
                <a href="/web" class="btn btn-blue">Open Env Explorer</a>
                <a href="/docs" class="btn btn-outline">API Docs (Swagger)</a>
            </div>
            <p style="margin-top:20px; font-size:0.9em;">Evaluation URL: <span class="badge">/reset</span></p>
        </div>
    </body>
    </html>
    """


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
