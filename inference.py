#!/usr/bin/env python3
"""
PatchHawk inference script — runs the LLM agent loop against the
OpenEnv-compliant PatchHawkEnv.

Environment variables:
    API_BASE_URL   – OpenAI-compatible API endpoint (required unless DRY_RUN=1)
    MODEL_NAME     – Model identifier (default: meta-llama/Llama-3.2-3B-Instruct)
    HF_TOKEN       – HuggingFace token (used as API key)
    TASK           – Run a single task id (easy_typosquat | medium_obfuscated | hard_patch)
    DRY_RUN        – Set to "1" to skip LLM calls and always BLOCK_PR

Usage:
    python inference.py                 # run all tasks via LLM
    DRY_RUN=1 python inference.py       # dry-run with static mock actions
    TASK=easy_typosquat python inference.py
"""

from __future__ import annotations

import json
import os
import sys
import traceback
from typing import List, Optional, Tuple

from patchhawk.agent.environment import PatchHawkEnv
from patchhawk.env_models import PatchHawkAction, PatchHawkObservation, PatchHawkReward
from patchhawk import tasks as graders

# ── Configuration ────────────────────────────────────────────────────

API_BASE_URL = os.getenv(
    "API_BASE_URL", "https://router.huggingface.co/hf-inference/v1"
)
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-Coder-32B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN", "")
DRY_RUN = os.getenv("DRY_RUN", "0") == "1"
SINGLE_TASK = os.getenv("TASK", "")

TASK_DEFS = [
    {
        "id": "easy_typosquat",
        "grader": graders.grade_easy,
        "max_steps": 5,
    },
    {
        "id": "medium_obfuscated",
        "grader": graders.grade_medium,
        "max_steps": 5,
    },
    {
        "id": "hard_patch",
        "grader": graders.grade_hard,
        "max_steps": 8,
    },
]

# ── Prompt builder ───────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are PatchHawk, a security agent that detects supply-chain vulnerabilities
in Python code. You will be given a code snippet and static analysis flags.

Respond with a JSON object containing:
{
  "action_type": <int>,     // 0=ANALYZE, 1=EXECUTE_SANDBOX, 2=BLOCK_PR, 3=SUBMIT_PATCH, 4=REQUEST_REVIEW
  "patch_content": <str|null>  // required if action_type == 3
}

Be decisive. If the code is clearly malicious, BLOCK_PR (2). If you can
generate a patch that removes the vulnerability, use SUBMIT_PATCH (3).
"""


def _build_user_prompt(obs: PatchHawkObservation, step: int) -> str:
    parts = [
        f"## Step {step}",
        f"**Code snippet:**\n```python\n{obs.code_snippet}\n```",
        f"**Static flags:** {obs.static_flags}",
        f"**Risk score:** {obs.risk_score}",
    ]
    if obs.sandbox_telemetry:
        parts.append(f"**Sandbox telemetry:**\n```\n{obs.sandbox_telemetry}\n```")
    parts.append("\nRespond with a JSON action object.")
    return "\n\n".join(parts)


# ── LLM caller ───────────────────────────────────────────────────────


def _call_llm(messages: list[dict]) -> str:
    """Call the OpenAI-compatible LLM and return the text content."""
    from openai import OpenAI

    client = OpenAI(
        base_url=API_BASE_URL,
        api_key=HF_TOKEN or "no-key",
    )
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=0.2,
        max_tokens=512,
    )
    return response.choices[0].message.content or ""


def _parse_action(text: str) -> PatchHawkAction:
    """Parse LLM response text into a PatchHawkAction."""
    # Try to extract JSON from the response
    text = text.strip()
    # Handle markdown code blocks
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    data = json.loads(text)
    return PatchHawkAction(
        action_type=int(data["action_type"]),
        patch_content=data.get("patch_content"),
    )


# ── Episode runner ───────────────────────────────────────────────────


def run_episode(
    env: PatchHawkEnv,
    task_id: str,
    max_steps: int,
    grader_fn,
) -> dict:
    """Run one episode and return summary dict."""
    obs = env.reset(task_id=task_id)

    print(f"[START] task={task_id} env=PatchHawk model={MODEL_NAME}")

    trajectory: List[Tuple[PatchHawkAction, PatchHawkObservation]] = []
    rewards: List[PatchHawkReward] = []
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    total_reward = 0.0
    step_num = 0
    error: Optional[str] = None

    while not obs.done and step_num < max_steps:
        step_num += 1

        # ── Choose action ────────────────────────────────────────
        if DRY_RUN:
            action = PatchHawkAction(action_type=PatchHawkEnv.ACTION_BLOCK_PR)
        else:
            try:
                user_msg = _build_user_prompt(obs, step_num)
                messages.append({"role": "user", "content": user_msg})
                llm_text = _call_llm(messages)
                messages.append({"role": "assistant", "content": llm_text})
                action = _parse_action(llm_text)
            except Exception as exc:
                error = str(exc)
                # Apply conservative BLOCK_PR constraint on malformed LLM responses
                action = PatchHawkAction(action_type=PatchHawkEnv.ACTION_BLOCK_PR)

        # ── Step ─────────────────────────────────────────────────
        obs = env.step(action)
        reward_val = obs.reward or 0.0
        reason = obs.metadata.get("reward_reason", "")
        step_reward = PatchHawkReward(value=float(reward_val), reason=reason)
        trajectory.append((action, obs))
        rewards.append(step_reward)
        total_reward += step_reward.value

        action_name = PatchHawkEnv.ACTION_NAMES[action.action_type]
        _done = str(obs.done).lower()
        _err = "null" if error is None else error
        print(
            f"[STEP] step={step_num} action={action_name} "
            f"reward={step_reward.value:.2f} done={_done} error={_err}",
            flush=True,
        )
        error = None  # reset for next step

    # ── Grade ────────────────────────────────────────────────────
    score = grader_fn(env, trajectory)

    rewards_str = ",".join(f"{r.value:.2f}" for r in rewards)
    success = score >= 1.0
    print(
        f"[END] success={str(success).lower()} steps={step_num} "
        f"score={score:.2f} rewards={rewards_str}",
        flush=True,
    )

    return {
        "task_id": task_id,
        "success": success,
        "steps": step_num,
        "score": score,
        "total_reward": total_reward,
    }


# ── Main ─────────────────────────────────────────────────────────────


def main():
    env = PatchHawkEnv(use_docker=False)

    task_list = TASK_DEFS
    if SINGLE_TASK:
        task_list = [t for t in TASK_DEFS if t["id"] == SINGLE_TASK]
        if not task_list:
            print(f"Unknown task: {SINGLE_TASK}", file=sys.stderr)
            sys.exit(1)

    results = []
    for task in task_list:
        try:
            result = run_episode(
                env,
                task_id=task["id"],
                max_steps=task["max_steps"],
                grader_fn=task["grader"],
            )
            results.append(result)
        except Exception:
            traceback.print_exc()
            results.append({"task_id": task["id"], "success": False, "error": True})

    env.close()

    # Summary
    print("\n=== Summary ===")
    for r in results:
        print(
            f"  {r['task_id']}: success={r.get('success')} score={r.get('score', 'N/A')}"
        )


if __name__ == "__main__":
    # Support --dry-run flag
    if "--dry-run" in sys.argv:
        os.environ["DRY_RUN"] = "1"
        # Re-read
        globals()["DRY_RUN"] = True
    main()
