"""
PatchHawk OpenEnv server entry point.
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

def main(port: int | None = None) -> None:
    """Start the PatchHawk OpenEnv server."""
    import uvicorn

    if port is None:
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
