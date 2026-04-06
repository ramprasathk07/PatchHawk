"""Tests for PatchHawkEnv (OpenEnv compliance + reward logic)."""

import pytest
from patchhawk.agent.environment import PatchHawkEnv
from patchhawk.env_models import PatchHawkAction, PatchHawkObservation, PatchHawkState


@pytest.fixture
def env():
    """Create a PatchHawkEnv with the default scenarios file."""
    e = PatchHawkEnv(use_docker=False)
    yield e
    e.close()


# ── Basic API ─────────────────────────────────────────────────────


def test_reset_returns_observation(env):
    """reset() returns a PatchHawkObservation (OpenEnv API)."""
    obs = env.reset()
    assert isinstance(obs, PatchHawkObservation)
    assert hasattr(obs, "code_snippet")
    assert hasattr(obs, "static_flags")
    assert hasattr(obs, "risk_score")
    assert hasattr(obs, "done")
    assert hasattr(obs, "reward")
    assert hasattr(obs, "metadata")


def test_observation_fields(env):
    """Verify observation field types."""
    obs = env.reset()
    assert isinstance(obs.code_snippet, str)
    assert isinstance(obs.static_flags, list)
    assert isinstance(obs.risk_score, float)
    assert isinstance(obs.done, bool)
    assert isinstance(obs.metadata, dict)


def test_step_returns_observation(env):
    """step() returns a PatchHawkObservation (OpenEnv API)."""
    env.reset()
    action = PatchHawkAction(action_type=env.ACTION_ANALYZE)
    obs = env.step(action)
    assert isinstance(obs, PatchHawkObservation)
    assert isinstance(obs.reward, (int, float))
    assert isinstance(obs.done, bool)
    assert isinstance(obs.metadata, dict)


def test_state_property(env):
    """state property returns a PatchHawkState."""
    env.reset()
    state = env.state
    assert isinstance(state, PatchHawkState)
    assert hasattr(state, "episode_id")
    assert hasattr(state, "step_count")
    assert hasattr(state, "scenario_id")


def test_all_action_types_accepted(env):
    """All five action types (0-4) are accepted."""
    for action_type in range(5):
        obs = env.reset()
        action = PatchHawkAction(action_type=action_type)
        result = env.step(action)
        assert isinstance(result, PatchHawkObservation)


# ── Reward logic ──────────────────────────────────────────────────


def test_block_malicious_positive_reward(env):
    malicious = [s for s in env.scenarios if s.get("label") == "malicious"]
    if not malicious:
        pytest.skip("No malicious scenarios available")
    env.reset(scenario=malicious[0])
    action = PatchHawkAction(action_type=env.ACTION_BLOCK_PR)
    obs = env.step(action)
    assert obs.reward == 2.0
    assert obs.done is True


def test_block_benign_negative_reward(env):
    benign = [s for s in env.scenarios if s.get("label") == "benign"]
    if not benign:
        pytest.skip("No benign scenarios available")
    env.reset(scenario=benign[0])
    action = PatchHawkAction(action_type=env.ACTION_BLOCK_PR)
    obs = env.step(action)
    assert obs.reward == -1.0
    assert obs.done is True


def test_execute_sandbox_reward(env):
    env.reset()
    action = PatchHawkAction(action_type=env.ACTION_EXECUTE_SANDBOX)
    obs = env.step(action)
    assert obs.reward == 0.1
    assert obs.done is False


def test_analyze_no_reward(env):
    env.reset()
    action = PatchHawkAction(action_type=env.ACTION_ANALYZE)
    obs = env.step(action)
    assert obs.reward == 0.0
    assert obs.done is False


def test_request_review_terminates(env):
    env.reset()
    action = PatchHawkAction(action_type=env.ACTION_REQUEST_REVIEW)
    obs = env.step(action)
    assert obs.reward == 0.0
    assert obs.done is True


def test_max_steps_penalty(env):
    malicious = [s for s in env.scenarios if s.get("label") == "malicious"]
    if not malicious:
        pytest.skip("No malicious scenarios available")
    env.reset(scenario=malicious[0])
    action = PatchHawkAction(action_type=env.ACTION_ANALYZE)
    obs = None
    for _ in range(env.max_steps):
        obs = env.step(action)
        if obs.done:
            break
    # Last step on malicious without block/patch → -5.0
    assert obs.reward == -5.0
    assert obs.done is True


def test_episode_with_scenario_kwarg(env):
    """Verify that passing a scenario via kwargs works."""
    scenario = {
        "id": "test_custom",
        "type": "functional",
        "label": "benign",
        "code_snippet": "x = 42",
        "patch": None,
        "unit_test_code": None,
        "attack_type": None,
    }
    obs = env.reset(scenario=scenario)
    assert obs.code_snippet == "x = 42"
    assert obs.metadata["scenario_id"] == "test_custom"


def test_step_counter_increments(env):
    """Verify step counter tracks correctly."""
    env.reset()
    for i in range(3):
        action = PatchHawkAction(action_type=env.ACTION_ANALYZE)
        env.step(action)
    assert env.state.step_count == 3


def test_close_resets_scenario(env):
    """close() clears episode state."""
    env.reset()
    env.close()
    assert env.current_scenario is None
