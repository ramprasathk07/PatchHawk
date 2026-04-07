#!/usr/bin/env python3
"""
PatchHawk inference script — runs the LLM agent loop against the
OpenEnv-compliant PatchHawkEnv.
a
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
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

API_BASE_URL = os.getenv(
    "API_BASE_URL", "https://router.huggingface.co/hf-inference/v1"
)
# Prefer explicit MODEL_NAME, fallback to GRPO_POLICY_MODEL from .env, then default to 32B model.
MODEL_NAME = os.getenv("MODEL_NAME", os.getenv("GRPO_POLICY_MODEL", "Qwen/Qwen2.5-Coder-32B-Instruct"))
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
You are PatchHawk, a highly critical security agent that detects supply-chain vulnerabilities in Python code.

Given a code snippet, your goal is to decide the safest path forward. 

## 🎯 Your Decision Heuristics:
1.  **Risk Score Calibration**:
    -   **0.9 - 1.0 (CRITICAL)**: Code contains obvious backdoors, remote shells, `base64` obfuscated `exec`, or unauthorized `os.system` calls.
    -   **0.5 - 0.8 (HIGH)**: Suspicious imports, typosquatting (e.g. `requests` -> `requesst`), or insecure usage of `eval`.
    -   **0.0 - 0.2 (LOW)**: Benign, standard Python code.
2.  **Action Selection**:
    -   **0 ANALYZE**: Standard observation for low-risk code.
    -   **1 EXECUTE_SANDBOX**: Choose this if you see suspicious activity but need to confirm if it makes network calls or writes files. 
    -   **2 BLOCK_PR**: Use for unfixable, malicious backdoors.
    -   **3 SUBMIT_PATCH**: If the code has a fixable vulnerability (e.g. lack of sanitization, typo), you **MUST** provide the corrected code in `patch_content`.
    -   **4 REQUEST_REVIEW**: Only for extreme ambiguity.

## 📝 Rules for Output JSON:
-   **EXACT JSON ONLY**. No markdown blocks, no extra text.
-   **Patch Content**: If `action_type` is 3, `patch_content` **CANNOT** be null. It must be the full, corrected Python script.
-   **Risk Score**: Be precise. Do not default to 0.0 if you see any suspicious imports.

## Response Format:
{
  "reasoning": "Step-by-step security analysis...",
  "risk_score": <float>,
  "action_type": <int>,
  "patch_content": "<str|null>"
}
"""

# SYSTEM_PROMPT = """\
# You are PatchHawk, a security agent that detects supply-chain vulnerabilities
# in Python code. You will be given a code snippet and static analysis flags.

# Respond EXACTLY with a JSON object containing the following keys:
# {
#   "reasoning": "<str>",         // Step-by-step explanation of what the vulnerability is, why you are blocking/patching it, and how it can be fixed.
#   "risk_score": <float>,        // Your predicted risk score from 0.0 to 1.0 based on your analysis
#   "action_type": <int>,         // 0=ANALYZE, 1=EXECUTE_SANDBOX, 2=BLOCK_PR, 3=SUBMIT_PATCH, 4=REQUEST_REVIEW
#   "patch_content": "<str|null>" // The full patched python code fixing the vulnerability
# }

# Be decisive. First, explain your findings thoroughly in the "reasoning" field.
# If the code is malicious but you can fix the vulnerability, use SUBMIT_PATCH (3) and provide the safe, corrected code in "patch_content".
# If the code is severely malicious and completely unfixable, use BLOCK_PR (2).
# IMPORTANT: Ensure your output is perfectly VALID JSON. Escape all double quotes inside strings properly.
# """


def _build_user_prompt(obs: PatchHawkObservation, step: int) -> str:
    parts = [
        f"## Step {step}",
        f"**Target Code Snippet:**\n```python\n{obs.code_snippet}\n```",
        f"**Environment Analysis Flags:** {obs.static_flags}",
        f"**Environment Initial Risk Assessment:** {obs.risk_score}",
    ]
    if obs.sandbox_telemetry:
        parts.append(f"**Sandbox Telemetry (Crucial Evidence):**\n```\n{obs.sandbox_telemetry}\n```")
    
    parts.append("\n**TASK:** Based on the above code and evidence, provide your own `risk_score` and decide the next `action_type`. If suspicious but unconfirmed, use EXECUTE_SANDBOX (1) to collect telemetry.")
    parts.append("Respond with the required JSON object only.")
    return "\n\n".join(parts)


# ── LLM caller ───────────────────────────────────────────────────────


_local_pipeline = None

def _call_llm_local(messages: list[dict]) -> str:
    """Call a local HuggingFace model using transformers pipeline if remote API fails."""
    global _local_pipeline
    if _local_pipeline is None:
        import torch
        from transformers import pipeline
        
        # User is already using this model in .env GRPO_POLICY_MODEL
        local_model = os.getenv("GRPO_POLICY_MODEL", "unsloth/Qwen2.5-Coder-3B-Instruct")
        print(f"\n[Fallback] Loading local model: {local_model} into memory. This may take a moment...", flush=True)
        
        _local_pipeline = pipeline(
            "text-generation",
            model=local_model,
            model_kwargs={"torch_dtype": torch.bfloat16},  # Half-precision to save VRAM natively fit on 12GB
            device_map="auto"
        )
        print("[Fallback] Local model loaded successfully.\n", flush=True)

    # Format messages array to a standard conversational string format
    prompt = _local_pipeline.tokenizer.apply_chat_template(
        messages, 
        tokenize=False, 
        add_generation_prompt=True
    )
    
    # Run Generation
    outputs = _local_pipeline(
        prompt,
        max_new_tokens=2048,
        do_sample=True,
        temperature=0.2,
    )
    
    generated = outputs[0]["generated_text"]
    
    print(f"\ngenerated:{generated}\n")
    # Strip prompt from returned generated output
    if generated.startswith(prompt):
        generated = generated[len(prompt):]
        
    return generated.strip()


def _call_llm(messages: list[dict]) -> str:
    """Call the OpenAI-compatible LLM and return the text content."""
    from openai import OpenAI

    try:
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
    except Exception as e:
        print(f"[LLM ERROR] Remote API failed: {e}. Initiating local Fallback...", flush=True)
        return _call_llm_local(messages)


import re

def _parse_action(text: str) -> PatchHawkAction:
    """Parse LLM response text into a PatchHawkAction."""
    text = text.strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text and not text.startswith("{"):
        text = text.split("```")[1].split("```")[0].strip()

    def clean_patch(p: str) -> str:
        if not p: return p
        if "```python" in p:
            return p.split("```python")[1].split("```")[0].strip()
        if "```" in p:
            return p.split("```")[1].split("```")[0].strip()
        return p

    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        action_match = re.search(r'"action_type"\s*:\s*(\d+)', text)
        action_type = int(action_match.group(1)) if action_match else 2
        
        risk_match = re.search(r'"risk_score"\s*:\s*([\d\.]+)', text)
        risk_score = float(risk_match.group(1)) if risk_match else None
        
        patch_match = re.search(r'"patch_content"\s*:\s*"(.*)', text, re.DOTALL)
        patch_content = None
        if patch_match:
            raw_patch = patch_match.group(1).rsplit('"', 1)[0]
            raw_patch = raw_patch.replace("\\n", "\n").replace('\\"', '"').replace("\\\\", "\\")
            patch_content = clean_patch(raw_patch)

        return PatchHawkAction(
            action_type=action_type,
            reasoning="JSON Error/Truncated Output. Recovered partial data.",
            predicted_risk=risk_score,
            patch_content=patch_content
        )

    return PatchHawkAction(
        action_type=int(data.get("action_type", 2)),
        patch_content=clean_patch(data.get("patch_content")),
        reasoning=data.get("reasoning"),
        predicted_risk=data.get("risk_score"),
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
