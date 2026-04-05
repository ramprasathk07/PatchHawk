"""
PatchHawk typed models — OpenEnv-compliant Pydantic models.

Extends openenv.core base types (Action, Observation, State) so the
environment is fully compatible with the OpenEnv framework.
"""

from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict, Field

from openenv.core import Action, Observation, State


# ── Observation ──────────────────────────────────────────────────────

class PatchHawkObservation(Observation):
    """Observation returned by PatchHawkEnv after reset() and step()."""

    code_snippet: str = Field(
        default="", description="Python source code to analyse"
    )
    static_flags: List[int] = Field(
        default_factory=list,
        description="Binary flags indicating static risk patterns",
    )
    risk_score: float = Field(
        default=0.0, description="Precomputed heuristic risk score 0-1"
    )
    sandbox_telemetry: Optional[str] = Field(
        None, description="Output from previous sandbox execution"
    )


# ── Action ───────────────────────────────────────────────────────────

class PatchHawkAction(Action):
    """Action submitted to PatchHawkEnv.step().

    action_type values:
        0 = ANALYZE
        1 = EXECUTE_SANDBOX
        2 = BLOCK_PR
        3 = SUBMIT_PATCH
        4 = REQUEST_REVIEW
    """

    action_type: int = Field(
        ...,
        description="0: ANALYZE, 1: EXECUTE_SANDBOX, 2: BLOCK_PR, "
                    "3: SUBMIT_PATCH, 4: REQUEST_REVIEW",
    )
    patch_content: Optional[str] = Field(
        None, description="The unified context patch if action is SUBMIT_PATCH"
    )


# ── State ────────────────────────────────────────────────────────────

class PatchHawkState(State):
    """Internal state of a PatchHawkEnv episode."""

    scenario_id: str = Field(default="", description="Current scenario ID")
    current_task: Optional[str] = Field(
        None, description="Active task_id (easy_typosquat, medium_obfuscated, hard_patch)"
    )
    last_action_type: Optional[int] = Field(
        None, description="Last action type taken"
    )
    patch_validated: bool = Field(
        default=False, description="Whether the last patch was validated"
    )
    sandbox_log: Optional[str] = Field(
        None, description="Most recent sandbox execution log"
    )


# ── Reward (standalone — no OpenEnv base type for rewards) ───────────

class PatchHawkReward(BaseModel):
    """Pydantic reward model used by graders and inference logging."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
    )

    value: float = Field(default=0.0, description="Numeric reward signal")
    reason: str = Field(default="", description="Human-readable reward reason")
