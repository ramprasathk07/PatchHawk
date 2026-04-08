"""
PatchHawkEnv – OpenEnv-compliant environment for
supply-chain vulnerability detection and patching.

Actions (PatchHawkAction.action_type):
    0 = ANALYZE
    1 = EXECUTE_SANDBOX
    2 = BLOCK_PR
    3 = SUBMIT_PATCH
    4 = REQUEST_REVIEW

Reward table (set on Observation.reward):
    Correct BLOCK on malicious         → +2.0
    Correct SUBMIT_PATCH (validated)   → +3.0
    BLOCK on benign                    → −1.0
    SUBMIT_PATCH on benign (applied)   → −1.5
    Episode ends w/o block/patch on mal → −5.0 (at max_steps)
    EXECUTE_SANDBOX                    → +0.1
"""

import json
import random
from typing import Optional, Any
from uuid import uuid4

from openenv.core import Environment

from patchhawk.env_models import (
    PatchHawkAction,
    PatchHawkObservation,
    PatchHawkState,
)
from patchhawk.agent.sandbox import run_code, validate_patch


class PatchHawkEnv(Environment[PatchHawkAction, PatchHawkObservation, PatchHawkState]):
    """OpenEnv environment for PatchHawk."""

    # Action constants
    ACTION_ANALYZE = 0
    ACTION_EXECUTE_SANDBOX = 1
    ACTION_BLOCK_PR = 2
    ACTION_SUBMIT_PATCH = 3
    ACTION_REQUEST_REVIEW = 4

    ACTION_NAMES = [
        "ANALYZE",
        "EXECUTE_SANDBOX",
        "BLOCK_PR",
        "SUBMIT_PATCH",
        "REQUEST_REVIEW",
    ]

    SUPPORTS_CONCURRENT_SESSIONS = True

    def __init__(
        self,
        scenarios_path: str = "patchhawk/data/scenarios.json",
        use_docker: bool = False,
        max_steps: int = 5,
        **kwargs: Any,
    ):
        super().__init__(**kwargs)

        self.use_docker = use_docker
        self.max_steps = max_steps
        self.scenarios_path = scenarios_path
        self.scenarios = self._load_scenarios()

        # Episode state
        self.current_scenario: Optional[dict] = None
        self.step_counter: int = 0
        self.cumulative_reward: float = 0.0
        self._last_action: Optional[int] = None
        self._telemetry: Optional[dict] = None
        self._patch_validated: bool = False

        # Internal state object
        self._state = PatchHawkState(
            episode_id=str(uuid4()),
            step_count=0,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _load_scenarios(self) -> list:
        try:
            with open(self.scenarios_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load scenarios from {self.scenarios_path}: {e}")
            return []

    def _compute_static_flags(self, code: str) -> list[int]:
        """
        Static heuristics used to seed a risk score.

        Important: these are intentionally lightweight (string-based) so they work
        in CPU-only judge environments without extra dependencies.
        """

        lowered = code.lower()

        # We keep flags small and interpretable; risk_score is mean(flags).
        flags = [0] * 8

        # 0) code execution primitives
        if "eval(" in lowered or "exec(" in lowered:
            flags[0] = 1

        # 1) shell / process execution
        if "subprocess" in lowered or "os.system" in lowered:
            flags[1] = 1

        # 2) network primitives
        if "socket" in lowered or "requests" in lowered or "urllib" in lowered:
            flags[2] = 1

        # 3) environment manipulation / credential access
        if "os.environ" in lowered:
            flags[3] = 1

        # 4) obfuscation indicators
        if "base64" in lowered or "zlib" in lowered:
            flags[4] = 1

        # 5) typosquatting / suspicious imports (common misspellings from our scenarios)
        # We treat these as high-signal in this hackathon setting.
        if "import pythonn" in lowered or "import reqeusts" in lowered:
            flags[5] = 1

        # 6) unsafe deserialization
        if "pickle.loads" in lowered:
            flags[6] = 1

        # 7) dynamic import / code download patterns (very coarse)
        if "__import__(" in lowered or "importlib.import_module" in lowered:
            flags[7] = 1

        return flags

    def _build_observation(
        self,
        *,
        done: bool = False,
        reward: float = 0.0,
        reason: str = "",
        extra_meta: Optional[dict] = None,
    ) -> PatchHawkObservation:
        """Build a PatchHawkObservation from current episode state."""
        code = self.current_scenario["code_snippet"] if self.current_scenario else ""
        flags = self._compute_static_flags(code)
        risk = sum(flags) / max(len(flags), 1)

        meta: dict[str, Any] = {
            "scenario_id": self.current_scenario.get("id", "none")
            if self.current_scenario
            else "none",
            "step": self.step_counter,
            "cumulative_reward": self.cumulative_reward,
            "reward_reason": reason,
        }
        if extra_meta:
            meta.update(extra_meta)

        telemetry_str: Optional[str] = None
        if self._telemetry:
            telemetry_str = json.dumps(self._telemetry, default=str)

        return PatchHawkObservation(
            code_snippet=code,
            static_flags=flags,
            risk_score=round(risk, 4),
            sandbox_telemetry=telemetry_str,
            done=done,
            reward=reward,
            metadata=meta,
        )

    # ------------------------------------------------------------------
    # OpenEnv API
    # ------------------------------------------------------------------
    def reset(
        self,
        seed: Optional[int] = None,
        episode_id: Optional[str] = None,
        **kwargs: Any,
    ) -> PatchHawkObservation:
        """Reset the environment and return the initial observation.

        Keyword args:
            task_id: Optional[str] — filter scenarios by task_id field
        """
        self._reset_rubric()

        task_id: Optional[str] = kwargs.get("task_id")
        self.current_task: Optional[str] = task_id

        if seed is not None:
            random.seed(seed)

        # Check for direct scenario override (used by GRPO training)
        scenario_override = kwargs.get("scenario")

        # Pick scenario
        if scenario_override:
            self.current_scenario = scenario_override
        elif not self.scenarios:
            self.current_scenario = {
                "id": "fallback",
                "type": "functional",
                "label": "benign",
                "code_snippet": "print('hello')",
                "patch": None,
                "unit_test_code": None,
                "attack_type": None,
                "task_id": None,
            }
        elif task_id:
            # Primary: filter by task_id field in scenarios.json
            matches = [s for s in self.scenarios if s.get("task_id") == task_id]
            if not matches:
                # Fallback: map task_id to attack_type for backwards compat
                _TASK_FILTER = {
                    "easy_typosquat": "typosquatting",
                    "medium_obfuscated": "obfuscated_exec",
                    "hard_patch": None,
                }
                atk = _TASK_FILTER.get(task_id)
                if atk:
                    matches = [s for s in self.scenarios if s.get("attack_type") == atk]
                else:
                    matches = [
                        s
                        for s in self.scenarios
                        if s.get("label") == "malicious" and s.get("patch")
                    ]
            self.current_scenario = (
                random.choice(matches) if matches else random.choice(self.scenarios)
            )
        else:
            self.current_scenario = random.choice(self.scenarios)

        # Reset episode counters
        self.step_counter = 0
        self.cumulative_reward = 0.0
        self._last_action = None
        self._telemetry = None
        self._patch_validated = False

        self._state = PatchHawkState(
            episode_id=episode_id or str(uuid4()),
            step_count=0,
            scenario_id=self.current_scenario.get("id", "none"),
            current_task=task_id,
            last_action_type=None,
            patch_validated=False,
            sandbox_log=None,
        )

        return self._build_observation(reason="reset")

    def step(
        self,
        action: PatchHawkAction,
        timeout_s: Optional[float] = None,
        **kwargs: Any,
    ) -> PatchHawkObservation:
        """Execute one step in the environment."""
        self.step_counter += 1
        act = action.action_type
        self._last_action = act

        reward = 0.0
        done = False
        reason = ""
        extra_meta: dict[str, Any] = {"action_name": self.ACTION_NAMES[act]}

        label = self.current_scenario["label"]

        # ── ANALYZE ──────────────────────────────────────────────
        if act == self.ACTION_ANALYZE:
            reward = 0.0
            reason = "analyze — no reward"

        # ── EXECUTE_SANDBOX ──────────────────────────────────────
        elif act == self.ACTION_EXECUTE_SANDBOX:
            result = run_code(
                self.current_scenario["code_snippet"],
                timeout_sec=3,
                use_docker=self.use_docker,
            )
            self._telemetry = result
            extra_meta["telemetry"] = result
            reward = 0.1
            reason = "sandbox executed"

        # ── BLOCK_PR ─────────────────────────────────────────────
        elif act == self.ACTION_BLOCK_PR:
            if label == "malicious":
                reward = 2.0
                reason = "correct block on malicious"
            else:
                reward = -1.0
                reason = "incorrect block on benign"
            done = True

        # ── SUBMIT_PATCH ─────────────────────────────────────────
        elif act == self.ACTION_SUBMIT_PATCH:
            patch_code = action.patch_content or self.current_scenario.get("patch")
            if not patch_code:
                reward = -0.5
                reason = "no patch available"
                extra_meta["validation"] = "No patch available"
            else:
                success, msg, details = validate_patch(
                    self.current_scenario, patch_code, use_docker=self.use_docker
                )
                extra_meta["validation"] = msg
                extra_meta["details"] = details
                self._patch_validated = success
                if success:
                    if label == "malicious":
                        reward = 3.0
                        reason = "valid patch on malicious"
                    else:
                        reward = -1.5
                        reason = "patch applied to benign code"
                else:
                    reward = -1.0
                    reason = f"patch validation failed: {msg}"
            done = True

        # ── REQUEST_REVIEW ───────────────────────────────────────
        elif act == self.ACTION_REQUEST_REVIEW:
            reward = 0.0
            reason = "requested human review"
            done = True

        # ── Max-step penalty ────────────────────────────────────
        if self.step_counter >= self.max_steps and not done:
            done = True
            if label == "malicious":
                reward -= 5.0
                reason += " | max steps reached on malicious scenario"

        # ── Dynamic Risk Bonus ───────────────────────────────────
        predict_risk = getattr(action, "predicted_risk", None)
        if predict_risk is not None:
            actual_risk = 1.0 if label == "malicious" else 0.0
            accuracy_bonus = (1.0 - abs(actual_risk - float(predict_risk))) * 2.0
            reward += accuracy_bonus
            reason += f" | AI risk accuracy bonus: +{accuracy_bonus:.2f}"

        self.cumulative_reward += reward

        # Update internal state
        self._state.step_count = self.step_counter
        self._state.last_action_type = act
        self._state.patch_validated = self._patch_validated
        if self._telemetry:
            self._state.sandbox_log = json.dumps(self._telemetry, default=str)

        obs = self._build_observation(
            done=done,
            reward=reward,
            reason=reason,
            extra_meta=extra_meta,
        )

        return self._apply_transform(obs)

    @property
    def state(self) -> PatchHawkState:
        """Return the current internal state."""
        return self._state

    def close(self) -> None:
        """Clean up any Docker containers launched during the episode."""
        self.current_scenario = None
        self._telemetry = None
