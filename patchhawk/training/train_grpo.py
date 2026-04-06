#!/usr/bin/env python3
"""
GRPO training pipeline for PatchHawk (trl 1.0.0, RTX 3060 12GB).

Fixed for trl 1.0.0:
- Removed max_prompt_length / max_completion_length.
- Disabled fp16 to avoid BFloat16 AMP error.
- Set tokenizer.model_max_length for sequence length control.
- Forced WandB logging every step via custom callback (no step argument to avoid warnings).
- Loss displayed in tqdm progress bar.
- WandB online mode forced before init.
"""

import argparse
import os
import random
import re
from pathlib import Path

import numpy as np

try:
    import wandb
except ImportError:
    wandb = None

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _build_prompt(scenario: dict) -> str:
    return (
        "Analyze this Python code for supply-chain vulnerabilities.\n"
        f"<code_snippet>\n{scenario['code_snippet']}\n</code_snippet>\n"
        "Respond in STRICT XML:\n"
        "<thought>...</thought>\n"
        "<action>0-4</action>\n"
        "<patch>...</patch> (ONLY if action=3)\n"
    )


def train_agent(args):
    # Check trl availability
    if not args.dry_run:
        try:
            from trl import GRPOTrainer, GRPOConfig
        except Exception as exc:
            raise RuntimeError(
                "trl not found.\nInstall: pip install trl==1.0.0 peft bitsandbytes accelerate transformers"
            ) from exc

    # ── WandB initialisation (force online mode before init) ──
    if not args.dry_run and wandb is not None:
        os.environ["WANDB_MODE"] = "online"
        os.environ["WANDB_SILENT"] = "false"
        wandb.init(
            project="patchhawk",
            name="grpo-run",
            config=vars(args),
        )
    else:
        print("[INFO] WandB skipped.")

    # ── Environment ──────────────────────────────────────────
    from patchhawk.agent.environment import PatchHawkEnv

    env = PatchHawkEnv(
        scenarios_path=str(_PROJECT_ROOT / "patchhawk" / "data" / "scenarios.json"),
        use_docker=args.use_docker,
    )
    print(f"Loaded {len(env.scenarios)} scenarios.")

    if args.dry_run:
        _dry_run_training(env, args)
        return

    # ── GPU training imports ─────────────────────────────────
    import torch
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainerCallback,
    )
    from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
    from datasets import Dataset
    from trl import GRPOConfig, GRPOTrainer

    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("No GPU found — training will be slow.")

    MODEL_NAME = "Qwen/Qwen2.5-Coder-3B-Instruct"

    # 4‑bit quantisation config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    print(f"Loading {MODEL_NAME} in 4-bit ...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "left"

    # Critical: set total sequence length (prompt + generation)
    tokenizer.model_max_length = args.max_seq_len

    base_model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        torch_dtype=torch.float16,
    )

    base_model = prepare_model_for_kbit_training(
        base_model,
        use_gradient_checkpointing=True,
    )

    # LoRA configuration
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=16,
        lora_dropout=0.05,
        bias="none",
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
    )
    model = get_peft_model(base_model, lora_config)
    model.print_trainable_parameters()

    # ── Reward 1: XML format ─────────────────────────────────
    def format_reward(completions, **kwargs):
        rewards = []
        for c in completions:
            text = c if isinstance(c, str) else str(c)
            score = 0.0
            if re.search(r"<thought>.*?</thought>", text, re.DOTALL):
                score += 0.5
            else:
                score -= 1.0
            if re.search(r"<action>[0-4]</action>", text):
                score += 0.5
            else:
                score -= 1.5
            if "<action>3</action>" in text:
                if re.search(r"<patch>.*?</patch>", text, re.DOTALL):
                    score += 0.5
                else:
                    score -= 2.0
            rewards.append(score)
        return rewards

    # ── Reward 2: environment feedback ───────────────────────
    from patchhawk.env_models import PatchHawkAction

    def env_reward(completions, prompts, **kwargs):
        rewards = []
        for prompt, c in zip(prompts, completions):
            text = c if isinstance(c, str) else str(c)

            # Extract code snippet from prompt to identify scenario
            code_match = re.search(r"<code_snippet>(.*?)</code_snippet>", prompt, re.DOTALL)
            if not code_match:
                rewards.append(-2.0)
                continue
            snippet = code_match.group(1).strip()
            scenario = None
            for s in env.scenarios:
                if s.get("code_snippet", "").strip() == snippet:
                    scenario = s
                    break
            if scenario is None:
                rewards.append(-2.0)
                continue

            # Parse action
            action_match = re.search(r"<action>(\d+)</action>", text)
            if not action_match:
                rewards.append(-2.0)
                continue
            action_type = int(action_match.group(1))

            # Parse patch (if any)
            patch = None
            patch_match = re.search(r"<patch>(.*?)</patch>", text, re.DOTALL)
            if patch_match:
                patch = patch_match.group(1).strip()

            try:
                # Reset environment to the exact scenario
                env.reset(scenario_idx=env.scenarios.index(scenario))
                obs = env.step(PatchHawkAction(action_type=action_type, patch_content=patch))
                rewards.append(float(obs.reward or 0.0))
            except Exception as exc:
                print(f"env_reward crash: {exc}")
                rewards.append(-3.0)
        return rewards

    # ── Dataset preparation ──────────────────────────────────
    valid = [s for s in env.scenarios if s.get("label") in ("malicious", "benign")]
    random.seed(42)
    random.shuffle(valid)

    split = int(0.8 * len(valid))
    train_ds = Dataset.from_list([{"prompt": _build_prompt(s)} for s in valid[:split]])
    eval_ds = Dataset.from_list([{"prompt": _build_prompt(s)} for s in valid[split:]])
    print(f"Dataset — train: {len(train_ds)}, eval: {len(eval_ds)}")

    # ── GRPO Config (trl 1.0.0 compatible) ───────────────────
    grpo_config = GRPOConfig(
        output_dir=args.output_dir,
        learning_rate=args.learning_rate,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        fp16=False,                     # avoids BFloat16 AMP error
        gradient_checkpointing=True,
        num_generations=args.group_size,
        beta=args.kl_coef,
        num_train_epochs=args.epochs,
        warmup_steps=10,
        max_grad_norm=1.0,
        logging_steps=1,                # log every step
        logging_first_step=True,        # log step 0 immediately
        save_steps=50,
        report_to="wandb" if (wandb is not None and not args.dry_run) else "none",
    )

    # ── Custom callback: force WandB logging + progress bar (no step warnings) ──
    class ForceWandbCallback(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            if not logs:
                return
            # Log everything to wandb WITHOUT step argument (avoids step warnings)
            if wandb is not None and wandb.run is not None:
                wandb.log(logs)
            # Update progress bar with loss
            loss_key = None
            for key in ["loss", "grpo_loss", "train_loss"]:
                if key in logs:
                    loss_key = key
                    break
            if loss_key is not None:
                loss_val = logs[loss_key]
                if hasattr(state, "progress_bar") and state.progress_bar is not None:
                    state.progress_bar.set_postfix({loss_key: f"{loss_val:.4f}"})

    trainer = GRPOTrainer(
        model=model,
        reward_funcs=[format_reward, env_reward],
        args=grpo_config,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
    )
    trainer.add_callback(ForceWandbCallback())

    print("Starting GRPO training ...")
    trainer.train()

    # Ensure all pending logs are sent to wandb
    if wandb is not None and wandb.run is not None:
        wandb.finish()

    # ── Save LoRA adapter ────────────────────────────────────
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(out))
    tokenizer.save_pretrained(str(out))
    print(f"LoRA adapter saved to {out}")

    # ── Optional HF Hub upload ───────────────────────────────
    hf_repo = os.getenv("HF_REPO", "")
    if hf_repo:
        try:
            model.push_to_hub(hf_repo)
            tokenizer.push_to_hub(hf_repo)
            print(f"Uploaded to https://huggingface.co/{hf_repo}")
        except Exception as exc:
            print(f"HF upload failed: {exc}")


# ─────────────────────────────────────────────────────────────
# Dry-run (CPU simulation, no model)
# ─────────────────────────────────────────────────────────────
def _dry_run_training(env, args):
    print("[DRY RUN] CPU simulation only — no model loaded.\n")
    from patchhawk.env_models import PatchHawkAction

    def heuristic_policy(obs):
        risk = obs.risk_score
        if risk > 0.5:
            return PatchHawkAction(action_type=env.ACTION_BLOCK_PR)
        elif risk > 0.2:
            return PatchHawkAction(action_type=env.ACTION_EXECUTE_SANDBOX)
        return PatchHawkAction(action_type=env.ACTION_REQUEST_REVIEW)

    for epoch in range(args.epochs):
        print(f"── Epoch {epoch + 1}/{args.epochs} ──")
        epoch_rewards = []
        attack_success = {}

        for _ in range(0, min(len(env.scenarios), args.max_steps), args.group_size):
            group_rewards = []
            for _ in range(args.group_size):
                obs = env.reset()
                ep_reward = 0.0
                steps = 0
                while not obs.done and steps < env.max_steps:
                    obs = env.step(heuristic_policy(obs))
                    ep_reward += float(obs.reward or 0.0)
                    steps += 1
                group_rewards.append(ep_reward)

                label = env.current_scenario.get("label", "benign")
                atype = env.current_scenario.get("attack_type", "none") or "none"
                attack_success.setdefault(atype, {"correct": 0, "total": 0})
                attack_success[atype]["total"] += 1
                if (label == "malicious" and ep_reward > 0) or (label == "benign" and ep_reward >= 0):
                    attack_success[atype]["correct"] += 1

            mean_r = float(np.mean(group_rewards))
            std_r = float(np.std(group_rewards)) + 1e-8
            advantages = [(r - mean_r) / std_r for r in group_rewards]
            epoch_rewards.append(mean_r)
            print(f"  Batch mean_reward={mean_r:+.2f}  advantages={[f'{a:+.2f}' for a in advantages]}")

        epoch_mean = float(np.mean(epoch_rewards)) if epoch_rewards else 0.0
        print(f"  Epoch {epoch + 1} mean_reward: {epoch_mean:+.2f}")
        for atype, counts in attack_success.items():
            rate = counts["correct"] / max(counts["total"], 1)
            print(f"    {atype}: {rate:.0%} ({counts['correct']}/{counts['total']})")

        if wandb is not None:
            try:
                log_data = {
                    "epoch": epoch + 1,
                    "mean_reward": epoch_mean,
                    "loss": max(0.0, 1.0 - epoch_mean / 3.0),
                }
                for atype, counts in attack_success.items():
                    log_data[f"success_rate/{atype}"] = counts["correct"] / max(counts["total"], 1)
                wandb.log(log_data)
            except Exception:
                pass

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "adapter_config.json").write_text('{"model_type":"patchhawk-grpo-dry-run"}')
    (out / "adapter_model.bin").write_bytes(b"\x00" * 64)
    print(f"\n[DRY RUN] Dummy adapter written to {args.output_dir}/")


# ─────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PatchHawk GRPO Training (trl 1.0.0)")
    parser.add_argument("--dry-run", action="store_true", help="CPU simulation, no model")
    parser.add_argument("--use-docker", action="store_true", help="Use Docker sandbox")
    parser.add_argument("--max-seq-len", type=int, default=1024, help="Total sequence length (prompt+completion)")
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument("--kl-coef", type=float, default=0.01)
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    parser.add_argument("--group-size", type=int, default=4)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=200)
    parser.add_argument("--output-dir", type=str, default="grpo_lora")
    args = parser.parse_args()
    train_agent(args)