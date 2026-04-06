"""
PatchHawk HTTP Server — OpenEnv-compliant environment server.

Serves PatchHawkEnv over HTTP/WebSocket using openenv.core.create_app.
Also includes the legacy A2A endpoints for backwards-compatibility.

Run:
    python -m patchhawk.agent.server
    python -m patchhawk.agent.server --port 7860
"""

from __future__ import annotations

import os
import sys
from typing import Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from openenv.core import create_app

from patchhawk.agent.environment import PatchHawkEnv
from patchhawk.env_models import PatchHawkAction, PatchHawkObservation


# ── OpenEnv factory ───────────────────────────────────────────────

def _env_factory() -> PatchHawkEnv:
    """Factory callable for create_app — returns a fresh PatchHawkEnv."""
    scenarios_path = os.getenv(
        "PATCHHAWK_SCENARIOS", "patchhawk/data/scenarios.json"
    )
    return PatchHawkEnv(scenarios_path=scenarios_path, use_docker=False)


# ── OpenEnv app (primary) ─────────────────────────────────────────

openenv_app = create_app(
    _env_factory,
    PatchHawkAction,
    PatchHawkObservation,
    env_name="PatchHawk",
)


# ── Legacy A2A schemas ────────────────────────────────────────────

class ActRequest(BaseModel):
    code_snippet: str = Field(..., description="Python source code to analyse")


class ActResponse(BaseModel):
    decision: str = Field(..., description="Agent decision (BLOCK_PR, SUBMIT_PATCH, etc.)")
    patch: Optional[str] = Field(None, description="Proposed patch code, if any")
    confidence: float = Field(..., description="Agent confidence score 0-1")
    reward: float = Field(0.0, description="Total episode reward")
    details: Optional[dict] = None


class AgentCard(BaseModel):
    name: str = "PatchHawk"
    description: str = (
        "RL-powered supply-chain vulnerability detector and auto-patcher. "
        "Trained via GRPO on Qwen2.5-Coder-7B with Docker-sandboxed validation."
    )
    capabilities: list = [
        "code_analysis",
        "vulnerability_detection",
        "auto_patching",
        "sandbox_execution",
    ]
    input_schema: dict = {
        "type": "object",
        "properties": {
            "code_snippet": {"type": "string", "description": "Python source code to analyse"},
        },
        "required": ["code_snippet"],
    }
    output_schema: dict = {
        "type": "object",
        "properties": {
            "decision": {"type": "string"},
            "patch": {"type": "string", "nullable": True},
            "confidence": {"type": "number"},
            "reward": {"type": "number"},
        },
    }


# ── Singleton env for A2A ─────────────────────────────────────────

_env: Optional[PatchHawkEnv] = None


def _get_env() -> PatchHawkEnv:
    global _env
    if _env is None:
        scenarios_path = os.getenv(
            "PATCHHAWK_SCENARIOS", "patchhawk/data/scenarios.json"
        )
        _env = PatchHawkEnv(scenarios_path=scenarios_path, use_docker=False)
    return _env


# ── Mount A2A routes on the OpenEnv app ───────────────────────────

app = openenv_app


@app.get("/agent/card", response_model=AgentCard)
def agent_card():
    """Return agent identity and capabilities."""
    return AgentCard()


@app.post("/agent/act", response_model=ActResponse)
def agent_act(request: ActRequest):
    """
    Run a heuristic agent for one episode on the supplied code snippet.
    Uses risk-score based heuristic policy (MVP stand-in for trained model).
    """
    env = _get_env()

    scenario = {
        "id": "a2a_request",
        "type": "unknown",
        "label": "unknown",
        "code_snippet": request.code_snippet,
        "patch": None,
        "unit_test_code": None,
        "attack_type": None,
    }

    # Force this scenario
    obs = env.reset(scenario=scenario)

    total_reward = 0.0
    decision_action = None

    while not obs.done:
        risk = obs.risk_score

        # Heuristic policy (MVP stand-in for trained model)
        if risk > 0.6:
            action = PatchHawkAction(action_type=PatchHawkEnv.ACTION_BLOCK_PR)
        elif risk > 0.3:
            action = PatchHawkAction(action_type=PatchHawkEnv.ACTION_EXECUTE_SANDBOX)
        else:
            action = PatchHawkAction(action_type=PatchHawkEnv.ACTION_REQUEST_REVIEW)

        obs = env.step(action)
        total_reward += (obs.reward or 0.0)
        decision_action = action.action_type

    confidence = min(1.0, max(0.0, 0.5 + total_reward / 6.0))

    return ActResponse(
        decision=PatchHawkEnv.ACTION_NAMES[decision_action] if decision_action is not None else "ANALYZE",
        patch=None,
        confidence=round(confidence, 2),
        reward=round(total_reward, 2),
        details=obs.metadata,
    )


# ── CLI entry point ──────────────────────────────────────────────

def main():
    import uvicorn

    port = 8000
    # Parse --port flag
    args = sys.argv[1:]
    if "--port" in args:
        idx = args.index("--port")
        if idx + 1 < len(args):
            port = int(args[idx + 1])

    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
