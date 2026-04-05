"""
GRPO training pipeline for PatchHawk.

Uses:
    - unsloth  → Qwen2.5-Coder-7B in 4-bit with LoRA adapters
    - trl      → GRPOTrainer with environment-derived rewards
    - wandb    → public logging (project: patchhawk)
    - HF Hub   → adapter upload after training

Dry-run mode (``--dry-run``) simulates training on CPU without any
heavy ML dependencies.
"""

import argparse
import os
import random
import sys
from pathlib import Path

import numpy as np

try:
    import wandb
except ImportError:
    wandb = None

# Resolve project root for relative paths
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def _build_prompt(scenario: dict) -> str:
    """Convert a scenario into a training prompt."""
    return (
        "Analyze this Python code for supply-chain vulnerabilities.\n"
        f"<code_snippet>\n{scenario['code_snippet']}\n</code_snippet>\n"
        "Your response MUST include a thought process in <thought> tags "
        "and a final action (0-4) in <action> tags.\n"
        "0: ANALYZE, 1: EXECUTE_SANDBOX, 2: BLOCK_PR, "
        "3: SUBMIT_PATCH, 4: REQUEST_REVIEW.\n"
        "If you choose action 3, you MUST also provide the corrected code inside <patch> tags."
    )


def train_agent(args):
    """Main entry-point for GRPO training."""

    # ── 1. WandB ──────────────────────────────────────────────────
    if not args.dry_run and wandb is not None:
        wandb.init(
            project="patchhawk",
            name="grpo-run-1",
            config=vars(args),
        )
    else:
        print("[DRY RUN] WandB initialisation skipped.")

    # ── 2. Environment ────────────────────────────────────────────
    from patchhawk.agent.environment import PatchHawkEnv

    env = PatchHawkEnv(
        scenarios_path=str(_PROJECT_ROOT / "patchhawk" / "data" / "scenarios.json"),
        use_docker=args.use_docker,
    )
    print(f"Loaded environment with {len(env.scenarios)} scenarios.")

    # ── 3. Model ──────────────────────────────────────────────────
    if args.dry_run:
        _dry_run_training(env, args)
        return

    # Full GRPO training pipeline
    try:
        from unsloth import FastLanguageModel
        from trl import GRPOTrainer, GRPOConfig
        from datasets import Dataset
        import re

        max_seq_length = args.max_seq_len

        # Load Qwen2.5-Coder-7B in 4-bit
        model, tokenizer = FastLanguageModel.from_pretrained(
            model_name="unsloth/Qwen2.5-Coder-7B-Instruct",
            max_seq_length=max_seq_length,
            load_in_4bit=True,
        )

        # Attach LoRA adapters
        model = FastLanguageModel.get_peft_model(
            model,
            r=16,
            target_modules=[
                "q_proj", "k_proj", "v_proj", "o_proj",
                "gate_proj", "up_proj", "down_proj",
            ],
            lora_alpha=16,
            lora_dropout=0,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=3407,
        )

        # ── Reward 1: Formatting Optimization ────────────────────────
        def format_reward_function(completions, **kwargs):
            """Reward the LLM for adhering to strict XML syntax patterns mimicking DeepSeek-Math."""
            rewards = []
            for completion in completions:
                text = completion[0]["content"] if isinstance(completion, list) else str(completion)
                reward = 0.0
                
                # Check for thought structure
                if re.search(r"<thought>.*?</thought>", text, re.DOTALL):
                    reward += 0.5
                else:
                    reward -= 1.0  # Heavy penalty for skipping Chain of Thought
                
                # Check for valid action structure
                if re.search(r"<action>[0-4]</action>", text):
                    reward += 0.5
                else:
                    reward -= 1.5  # Critical penalty for unstructured decisions
                
                # Check patch constraint
                if "<action>3</action>" in text:
                    if re.search(r"<patch>.*?</patch>", text, re.DOTALL):
                        reward += 0.5
                    else:
                        reward -= 2.0  # Massive penalty for claiming to patch but dropping the payload
                
                rewards.append(reward)
            return rewards

        # ── Reward 2: Functional Sandbox Execution ─────────────────
        def env_reward_function(completions, prompts, **kwargs):
            """Executes valid actions in the OpenEnv and measures structural correctness."""
            # Cache lookup mapping for high-throughput batch grading
            if not hasattr(env_reward_function, "_scenario_map"):
                env_reward_function._scenario_map = {s["code_snippet"][:100]: s for s in env.scenarios}

            rewards = []
            for prompt, completion in zip(prompts, completions):
                text = completion[0]["content"] if isinstance(completion, list) else str(completion)
                
                match_action = re.search(r"<action>(\d+)</action>", text)
                action_type = int(match_action.group(1)) if match_action else 0

                match_patch = re.search(r"<patch>(.*?)</patch>", text, re.DOTALL)
                patch_content = match_patch.group(1).strip() if match_patch else None

                # O(1)-ish fast mapping resolution
                target = None
                for key, s in env_reward_function._scenario_map.items():
                    if key in prompt:
                        target = s
                        break
                
                if target is None:
                    rewards.append(-3.0)  # Total hallucination / catastrophic misalignment
                    continue

                try:
                    obs = env.reset(scenario=target)
                    obs_after_step = env.step(PatchHawkAction(action_type=action_type, patch_content=patch_content))
                    rewards.append(obs_after_step.reward or 0.0)
                except Exception as e:
                    print(f"⚠️ Sandbox Crash / Invalid Context Escaped: {e}")
                    rewards.append(-3.0)  # Protect trainer from crashing, penalize agent bounds
                    
            return rewards

        # ── Dataset ──────────────────────────────────────────────
        from patchhawk.env_models import PatchHawkAction
        
        # Filter and split
        valid_scenarios = [s for s in env.scenarios if s.get("label") in ("malicious", "benign")]
        random.seed(42)
        random.shuffle(valid_scenarios)
        split_idx = int(len(valid_scenarios) * 0.8)
        train_scenarios = valid_scenarios[:split_idx]
        test_scenarios = valid_scenarios[split_idx:]
        
        train_data = [{"prompt": _build_prompt(s)} for s in train_scenarios]
        test_data = [{"prompt": _build_prompt(s)} for s in test_scenarios]
        
        train_dataset = Dataset.from_list(train_data)
        eval_dataset = Dataset.from_list(test_data)

        training_args = GRPOConfig(
            output_dir=args.output_dir,
            learning_rate=args.learning_rate,
            per_device_train_batch_size=args.per_device_train_batch_size,
            gradient_accumulation_steps=args.gradient_accumulation_steps,
            max_prompt_length=max_seq_length // 2,
            max_completion_length=max_seq_length // 2,
            num_generations=args.group_size,
            num_train_epochs=args.num_train_epochs,
            warmup_ratio=args.warmup_ratio,
            max_grad_norm=args.max_grad_norm,
            beta=args.kl_coef,
            save_steps=50,
            logging_steps=10,
            report_to="wandb",
        )

        trainer = GRPOTrainer(
            model=model,
            reward_funcs=[format_reward_function, env_reward_function],
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
        )

        trainer.train()

        # Save adapter locally
        model.save_pretrained_merged(args.output_dir, tokenizer, save_method="lora")
        print(f"✅ Adapter saved to {args.output_dir}")

        # Upload to Hugging Face Hub
        hf_repo = os.getenv("HF_REPO", "your-username/patchhawk")
        try:
            model.push_to_hub(hf_repo, tokenizer=tokenizer)
            print(f"✅ Uploaded adapter to https://huggingface.co/{hf_repo}")
        except Exception as e:
            print(f"⚠️ HF upload failed: {e}")

    except ImportError as e:
        print(f"⚠️ Missing dependency for full training: {e}")
        print("Falling back to dry-run mode…")
        _dry_run_training(env, args)


def _dry_run_training(env, args):
    """
    Simulate GRPO training without GPU / heavy deps.
    Uses a deterministic heuristic policy.
    """
    print("[DRY RUN] Simulating GRPO training with heuristic policy…")

    from patchhawk.env_models import PatchHawkAction

    def heuristic_policy(obs):
        # We know obs is PatchHawkObservation, so risk_score is a float
        risk = obs.risk_score
        if risk > 0.5:
            return PatchHawkAction(action_type=env.ACTION_BLOCK_PR)
        elif risk > 0.2:
            return PatchHawkAction(action_type=env.ACTION_EXECUTE_SANDBOX)
        return PatchHawkAction(action_type=env.ACTION_REQUEST_REVIEW)

    epochs = 3
    all_metrics = []

    for epoch in range(epochs):
        print(f"\n── Epoch {epoch + 1}/{epochs} ──")
        epoch_rewards = []
        attack_success: dict = {}

        for batch_start in range(0, min(len(env.scenarios), args.max_steps), args.group_size):
            group_rewards = []
            for g in range(args.group_size):
                obs = env.reset()
                done = False
                ep_reward = 0.0
                steps = 0

                while not done and steps < env.max_steps:
                    action = heuristic_policy(obs)
                    obs = env.step(action)
                    ep_reward += (obs.reward or 0.0)
                    steps += 1
                    done = obs.done

                group_rewards.append(ep_reward)

                # Track per-attack-type success
                label = env.current_scenario.get("label", "benign")
                atype = env.current_scenario.get("attack_type", "none") or "none"
                if atype not in attack_success:
                    attack_success[atype] = {"correct": 0, "total": 0}
                attack_success[atype]["total"] += 1
                if (label == "malicious" and ep_reward > 0) or (label == "benign" and ep_reward >= 0):
                    attack_success[atype]["correct"] += 1

            mean_r = float(np.mean(group_rewards))
            std_r = float(np.std(group_rewards)) + 1e-8
            advantages = [(r - mean_r) / std_r for r in group_rewards]
            epoch_rewards.append(mean_r)

            print(f"  Batch: mean_reward={mean_r:+.2f}  advantages={[f'{a:+.2f}' for a in advantages]}")

        epoch_mean = float(np.mean(epoch_rewards)) if epoch_rewards else 0.0
        print(f"  Epoch {epoch + 1} mean_reward: {epoch_mean:+.2f}")

        # Per-attack-type success rates
        for atype, counts in attack_success.items():
            rate = counts["correct"] / max(counts["total"], 1)
            print(f"    {atype}: {rate:.0%} ({counts['correct']}/{counts['total']})")

        if wandb is not None and not getattr(wandb, '_disabled', True):
            try:
                log_data = {
                    "epoch": epoch + 1,
                    "mean_reward": epoch_mean,
                    "loss": max(0, 1.0 - epoch_mean / 3.0),  # pseudo-loss
                }
                for atype, counts in attack_success.items():
                    log_data[f"success_rate/{atype}"] = counts["correct"] / max(counts["total"], 1)
                wandb.log(log_data)
            except Exception:
                pass

    # Save dummy adapter
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config.json").write_text('{"model_type": "patchhawk-grpo-dry-run"}')
    (output_dir / "adapter_model.bin").write_bytes(b"\x00" * 64)
    print(f"\n[DRY RUN] Dummy adapter saved to {args.output_dir}/")


# ── CLI ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PatchHawk GRPO Training")
    parser.add_argument("--dry-run", action="store_true", help="Simulate training without GPU")
    parser.add_argument("--use-docker", action="store_true", help="Use Docker sandbox in env")
    parser.add_argument("--learning-rate", type=float, default=5e-6)
    parser.add_argument("--group-size", type=int, default=4, help="GRPO group size")
    parser.add_argument("--max-seq-len", type=int, default=2048)
    parser.add_argument("--per-device-train-batch-size", type=int, default=2)
    parser.add_argument("--gradient-accumulation-steps", type=int, default=4)
    parser.add_argument("--num-train-epochs", type=int, default=3)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--kl-coef", type=float, default=0.01)
    parser.add_argument("--ppo-clip-eps", type=float, default=0.2)
    parser.add_argument("--output-dir", type=str, default="grpo_lora")

    args = parser.parse_args()
    train_agent(args)
