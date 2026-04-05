"""
PatchHawk task graders — referenced in openenv.yaml.

Each grader receives the environment and a trajectory (list of
(action, observation) tuples), and returns a float score in [0, 1].
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Tuple

if TYPE_CHECKING:
    from patchhawk.agent.environment import PatchHawkEnv
    from patchhawk.env_models import PatchHawkAction, PatchHawkObservation


# Action constants (mirrored from PatchHawkEnv)
_ANALYZE = 0
_EXECUTE_SANDBOX = 1
_BLOCK_PR = 2
_SUBMIT_PATCH = 3
_REQUEST_REVIEW = 4


def grade_easy(
    env: "PatchHawkEnv",
    trajectory: List[Tuple["PatchHawkAction", "PatchHawkObservation"]],
) -> float:
    """Easy task grader — typosquatting detection.

    Returns 1.0 if:
        - The last action is BLOCK_PR or SUBMIT_PATCH
        - The scenario's attack_type is "typosquatting"
    """
    if not trajectory:
        return 0.0

    last_action, _last_obs = trajectory[-1]
    scenario = env.current_scenario or {}

    if last_action.action_type in (_BLOCK_PR, _SUBMIT_PATCH):
        if scenario.get("attack_type") == "typosquatting":
            return 1.0
    return 0.0


def grade_medium(
    env: "PatchHawkEnv",
    trajectory: List[Tuple["PatchHawkAction", "PatchHawkObservation"]],
) -> float:
    """Medium task grader — obfuscated exec detection.

    Returns 1.0 if:
        - EXECUTE_SANDBOX was used at least once in the trajectory
        - The last action is BLOCK_PR or SUBMIT_PATCH
        - The scenario's attack_type is "obfuscated_exec"
    """
    if not trajectory:
        return 0.0

    used_sandbox = any(
        a.action_type == _EXECUTE_SANDBOX for a, _o in trajectory
    )
    last_action, _last_obs = trajectory[-1]
    scenario = env.current_scenario or {}

    if (
        used_sandbox
        and last_action.action_type in (_BLOCK_PR, _SUBMIT_PATCH)
        and scenario.get("attack_type") == "obfuscated_exec"
    ):
        return 1.0
    return 0.0


def grade_hard(
    env: "PatchHawkEnv",
    trajectory: List[Tuple["PatchHawkAction", "PatchHawkObservation"]],
) -> float:
    """Hard task grader — validated patch submission.

    Returns 1.0 if:
        - The last action is SUBMIT_PATCH
        - env.state.patch_validated is True
    """
    if not trajectory:
        return 0.0

    last_action, _last_obs = trajectory[-1]

    if (
        last_action.action_type == _SUBMIT_PATCH
        and env.state.patch_validated
    ):
        return 1.0
    return 0.0
