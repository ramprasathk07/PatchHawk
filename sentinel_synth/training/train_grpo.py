import os
import argparse
import numpy as np

try:
    import wandb
except ImportError:
    wandb = None

# In a real environment, we would also import:
# from unsloth import FastLanguageModel
# from trl import GRPOTrainer, GRPOConfig
# But for the hackathon prototype and safe execution without massive deps,
# we use mock classes in dry-run mode if the real ones aren't available.

from ..envs.sentinel_env import SentinelEnv

def train_agent(args):
    """
    Main training loop for Sentinel-Synth GRPO.
    """
    # 1. Setup WandB
    if not args.dry_run:
        wandb.init(project="sentinel-synth", name="grpo-qwen2.5-coder-7b", config=vars(args))
    else:
        print("[DRY RUN] WandB initialization skipped.")

    # 2. Load Environment
    env = SentinelEnv(use_docker=args.use_docker)
    print(f"Loaded environment with {len(env.scenarios)} scenarios.")

    # 3. Load Model (Mock or unsloth)
    if args.dry_run:
        print("[DRY RUN] Loading dummy model instead of Qwen2.5-Coder-7B in 4-bit...")
        def dummy_policy(obs):
            # Deterministic dummy policy for dry runs
            risk = obs["risk_score"][0]
            if risk > 0.5:
                 return 3 # ACTION_SUBMIT_PATCH
            return 0 # ACTION_ANALYZE
            
        # 4. Dummy Training Loop
        epochs = 3
        batch_size = 4
        
        for epoch in range(epochs):
            print(f"--- Epoch {epoch+1}/{epochs} ---")
            total_rewards = []
            
            for batch_idx in range(len(env.scenarios) // batch_size):
                trajectories = []
                for g in range(args.group_size):
                    obs, _ = env.reset()
                    done = False
                    trajectory_reward = 0
                    steps = 0
                    
                    while not done and steps < env.max_steps:
                        action = dummy_policy(obs)
                        obs, reward, done, _, info = env.step(action)
                        trajectory_reward += reward
                        steps += 1
                        
                    trajectories.append(trajectory_reward)
                
                # Mock GRPO Advantage calculation
                mean_reward = np.mean(trajectories)
                std_reward = np.std(trajectories) + 1e-8
                advantages = [(r - mean_reward) / std_reward for r in trajectories]
                
                total_rewards.append(mean_reward)
                print(f"Batch {batch_idx}: Mean Reward: {mean_reward:.2f}, Advantages: {[f'{a:.2f}' for a in advantages]}")
                
            print(f"Epoch {epoch+1} Mean Reward: {np.mean(total_rewards):.2f}")
            if not args.dry_run:
                wandb.log({"epoch": epoch+1, "mean_reward": np.mean(total_rewards)})
                
        print("[DRY RUN] Training complete. Saved dummy adapter to ./grpo_lora/")
    else:
        print("Initializing true GRPO training with trl and unsloth...")
        try:
            from unsloth import FastLanguageModel
            from unsloth import is_bfloat16_supported
            from trl import GRPOTrainer, GRPOConfig
            from datasets import Dataset
            
            max_seq_length = args.max_seq_len
            model, tokenizer = FastLanguageModel.from_pretrained(
                model_name="unsloth/Qwen2.5-Coder-7B-Instruct",
                max_seq_length=max_seq_length,
                load_in_4bit=True,
            )
            
            model = FastLanguageModel.get_peft_model(
                model,
                r=16,
                target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                                "gate_proj", "up_proj", "down_proj"],
                lora_alpha=16,
                lora_dropout=0,
                bias="none",
                use_gradient_checkpointing="unsloth",
                random_state=3407,
            )
            
            # Formulate training as text completion where PPO builds on top.
            # In GRPO, we can provide a reward function that evaluates completions.
            
            import re
            
            def env_reward_function(completions, prompts, **kwargs):
                """
                Extracts chosen action, runs env, returns reward array.
                Matches completions to their corresponding scenario from prompts.
                """
                rewards = []
                for prompt, completion in zip(prompts, completions):
                    # extract the action from the completion using regex
                    text = completion[0]["content"]
                    match = re.search(r"<action>(\d+)</action>", text)
                    if match:
                        try:
                            action = int(match.group(1))
                        except ValueError:
                            action = SentinelEnv.ACTION_ANALYZE
                    else:
                        action = SentinelEnv.ACTION_ANALYZE
                        
                    # Find which scenario this prompt belongs to
                    # (In a real setup we'd pass IDs, here we search by substring)
                    target_scenario = None
                    for s in env.scenarios:
                        if s["code_snippet"][:100] in prompt:
                            target_scenario = s
                            break
                    
                    if not target_scenario:
                        rewards.append(0.0)
                        continue
                        
                    # Reset env with this specific scenario
                    obs, info = env.reset(options={"scenario": target_scenario})
                    _, reward, _, _, _ = env.step(action)
                    rewards.append(reward)
                return rewards

            # We need a proper dataset of prompts
            prompt_data = [{"prompt": f"Analyze this Python code for supply-chain vulnerabilities.\n<code_snippet>\n{s['code_snippet']}\n</code_snippet>\nYour response MUST include a thought process in <thought> tags and a final action (0-4) in <action> tags.\n0: ANALYZE, 1: EXECUTE_SANDBOX, 2: BLOCK_PR, 3: SUBMIT_PATCH, 4: REQUEST_REVIEW."} for s in env.scenarios]
            dataset = Dataset.from_list(prompt_data)
            
            training_args = GRPOConfig(
                output_dir="grpo_lora",
                learning_rate=args.learning_rate,
                per_device_train_batch_size=1,
                gradient_accumulation_steps=args.gradient_accumulation_steps,
                max_prompt_length=args.max_seq_len // 2,
                max_completion_length=args.max_seq_len // 2,
                num_generations=args.group_size,
                max_steps=args.max_steps,
                save_steps=50,
                logging_steps=10,
                report_to="wandb",
            )
            
            trainer = GRPOTrainer(
                model=model,
                reward_funcs=[env_reward_function],
                args=training_args,
                train_dataset=dataset,
            )
            
            trainer.train()
            model.save_pretrained_merged("grpo_lora", tokenizer, save_method="lora")
            print("Training complete and adapter saved.")
        except ImportError as e:
            print(f"Skipping standard training fallback. Missing required dependency: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Run with mock components without GPU.")
    parser.add_argument("--use-docker", action="store_true", help="Use Docker for execution fallback in env.")
    parser.add_argument("--learning-rate", type=float, default=1e-6)
    parser.add_argument("--group-size", type=int, default=4)
    parser.add_argument("--max-seq-len", type=int, default=1024)
    
    args = parser.parse_args()
    train_agent(args)
