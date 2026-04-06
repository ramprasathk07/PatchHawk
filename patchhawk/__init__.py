"""
PatchHawk — RL-powered supply-chain vulnerability detection & auto-patching.

Built for the PyTorch OpenEnv AI Hackathon.
"""

import os
from pathlib import Path

import yaml

# ── .env loading (zero external deps) ─────────────────────────────


def _load_dotenv(path: str) -> dict:
    """Minimal .env parser — avoids requiring python-dotenv at import time."""
    env: dict = {}
    if not os.path.exists(path):
        return env
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                env[key] = value
                if value:
                    os.environ.setdefault(key, value)
    return env


# ── Resolve project root (one level up from this file) ────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_dotenv_raw = _load_dotenv(str(PROJECT_ROOT / ".env"))

ENV = {
    "SYNTH_GENERATOR_MODEL": os.getenv(
        "SYNTH_GENERATOR_MODEL",
        _dotenv_raw.get("SYNTH_GENERATOR_MODEL", "meta-llama/Llama-3.2-3B-Instruct"),
    ),
    "GRPO_POLICY_MODEL": os.getenv(
        "GRPO_POLICY_MODEL",
        _dotenv_raw.get("GRPO_POLICY_MODEL", "unsloth/Qwen2.5-Coder-7B-Instruct"),
    ),
    "WANDB_API_KEY": os.getenv("WANDB_API_KEY", _dotenv_raw.get("WANDB_API_KEY", "")),
    "WANDB_PROJECT": os.getenv("WANDB_PROJECT", _dotenv_raw.get("WANDB_PROJECT", "patchhawk")),
    "WANDB_RUN_NAME": os.getenv("WANDB_RUN_NAME", _dotenv_raw.get("WANDB_RUN_NAME", "grpo-run-1")),
    "HF_TOKEN": os.getenv("HF_TOKEN", _dotenv_raw.get("HF_TOKEN", "")),
    "HF_REPO": os.getenv("HF_REPO", _dotenv_raw.get("HF_REPO", "ramprasathk07/patchhawk")),
    "DOCKER_IMAGE": os.getenv("DOCKER_IMAGE", _dotenv_raw.get("DOCKER_IMAGE", "patchhawk-sandbox:latest")),
}

# ── config.yaml loading ──────────────────────────────────────────
_config_path = PROJECT_ROOT / "config.yaml"
if _config_path.exists():
    with open(_config_path) as fh:
        CFG = yaml.safe_load(fh)
else:
    CFG = {
        "data_generation": {
            "num_samples": 10,
            "output_format": "json",
            "benign_dir": "patchhawk/data/benign/",
            "scenarios_output": "patchhawk/data/scenarios.json",
            "sdk_config": "patchhawk/data/sdk_config.yaml",
        },
        "training": {
            "learning_rate": 1e-6,
            "group_size": 4,
            "max_seq_len": 1024,
            "max_steps": 100,
            "gradient_accumulation_steps": 4,
            "ppo_clip_eps": 0.2,
            "lora_r": 16,
            "lora_alpha": 16,
            "lora_dropout": 0,
            "output_dir": "grpo_lora",
        },
        "environment": {
            "max_steps": 5,
            "use_docker": False,
            "sandbox_timeout_sec": 5,
        },
    }
