"""
Centralized configuration loader for Sentinel-Synth.

Loads:
  - .env  → ENV dict (model names, API keys, secrets)
  - config.yaml → CFG dict (training hyperparameters, paths)

Usage:
    from sentinel_synth.config import ENV, CFG
"""

import os
import yaml
from pathlib import Path

# ---------- .env loading (no external dependency) ----------
def _load_dotenv(path: str):
    """Minimal .env parser — avoids requiring python-dotenv at import time."""
    env = {}
    if not os.path.exists(path):
        return env
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, value = line.partition("=")
                key = key.strip()
                value = value.strip()
                env[key] = value
                # Also set in os.environ so downstream libs (wandb) pick it up
                if value:
                    os.environ.setdefault(key, value)
    return env

# Resolve project root (two levels up from this file)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_dotenv_raw = _load_dotenv(str(_PROJECT_ROOT / ".env"))

ENV = {
    "SYNTH_GENERATOR_MODEL": os.getenv("SYNTH_GENERATOR_MODEL", _dotenv_raw.get("SYNTH_GENERATOR_MODEL", "meta-llama/Llama-3.2-3B-Instruct")),
    "GRPO_POLICY_MODEL":     os.getenv("GRPO_POLICY_MODEL",     _dotenv_raw.get("GRPO_POLICY_MODEL", "unsloth/Qwen2.5-Coder-7B-Instruct")),
    "WANDB_API_KEY":         os.getenv("WANDB_API_KEY",         _dotenv_raw.get("WANDB_API_KEY", "")),
    "WANDB_PROJECT":         os.getenv("WANDB_PROJECT",         _dotenv_raw.get("WANDB_PROJECT", "sentinel-synth")),
    "WANDB_RUN_NAME":        os.getenv("WANDB_RUN_NAME",        _dotenv_raw.get("WANDB_RUN_NAME", "grpo-qwen-coder-7b")),
}

# ---------- config.yaml loading ----------
_config_path = _PROJECT_ROOT / "config.yaml"
if _config_path.exists():
    with open(_config_path) as f:
        CFG = yaml.safe_load(f)
else:
    CFG = {
        "data_generation": {
            "num_samples": 10,
            "output_format": "json",
            "benign_dir": "sentinel_synth/data/benign/",
            "scenarios_output": "sentinel_synth/data/scenarios.json",
            "sdk_config": "sentinel_synth/data/sdk_config.yaml",
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
