"""Tests for PatchHawkEnv (OpenEnv compliance + reward logic)."""

import pytest
import numpy as np
from patchhawk.agent.environment import PatchHawkEnv


@pytest.fixture
def env():
    """Create a PatchHawkEnv with the default scenarios file."""
    e = PatchHawkEnv(use_docker=False)
    yield e


# ── Basic API ─────────────────────────────────────────────────────

def test_reset_returns_obs_and_info(env):
    obs, info = env.reset()
    assert isinstance(obs, dict)
    assert "code_snippet" in obs
    assert "static_flags" in obs
    assert "risk_score" in obs
    assert isinstance(info, dict)


def test_observation_shapes(env):
    obs, _ = env.reset()
    assert isinstance(obs["code_snippet"], str)
    assert obs["static_flags"].shape == (5,)
    assert obs["risk_score"].shape == (1,)


def test_step_returns_five_tuple(env):
    env.reset()
    result = env.step(0)  # ANALYZE
    assert len(result) == 5
    obs, reward, terminated, truncated, info = result
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)


def test_action_space_contains_all_actions(env):
    for a in range(5):
        assert env.action_space.contains(a)
    assert not env.action_space.contains(5)


# ── Reward logic ──────────────────────────────────────────────────

def test_block_malicious_positive_reward(env):
    malicious = [s for s in env.scenarios if s.get("label") == "malicious"]
    if not malicious:
        pytest.skip("No malicious scenarios available")
    obs, _ = env.reset(options={"scenario": malicious[0]})
    _, reward, terminated, _, _ = env.step(env.ACTION_BLOCK_PR)
    assert reward == 2.0
    assert terminated is True


def test_block_benign_negative_reward(env):
    benign = [s for s in env.scenarios if s.get("label") == "benign"]
    if not benign:
        pytest.skip("No benign scenarios available")
    obs, _ = env.reset(options={"scenario": benign[0]})
    _, reward, terminated, _, _ = env.step(env.ACTION_BLOCK_PR)
    assert reward == -1.0
    assert terminated is True


def test_execute_sandbox_reward(env):
    env.reset()
    _, reward, terminated, _, _ = env.step(env.ACTION_EXECUTE_SANDBOX)
    assert reward == 0.1
    assert terminated is False


def test_max_steps_truncation(env):
    malicious = [s for s in env.scenarios if s.get("label") == "malicious"]
    if not malicious:
        pytest.skip("No malicious scenarios available")
    obs, _ = env.reset(options={"scenario": malicious[0]})
    total_reward = 0.0
    for _ in range(env.max_steps):
        obs, reward, terminated, truncated, info = env.step(env.ACTION_ANALYZE)
        total_reward += reward
        if terminated or truncated:
            break
    # Last step on malicious without block/patch → -5.0
    assert reward == -5.0
    assert truncated is True


def test_render_does_not_crash(env, capsys):
    env.reset()
    env.step(env.ACTION_ANALYZE)
    env.render()
    captured = capsys.readouterr()
    assert "Step" in captured.out


def test_episode_with_scenario_option(env):
    """Verify that passing a scenario via options works."""
    scenario = {
        "id": "test_custom",
        "type": "functional",
        "label": "benign",
        "code_snippet": "x = 42",
        "patch": None,
        "unit_test_code": None,
        "attack_type": None,
    }
    obs, info = env.reset(options={"scenario": scenario})
    assert obs["code_snippet"] == "x = 42"
    assert info["scenario_id"] == "test_custom"
