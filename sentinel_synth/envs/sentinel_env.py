import gymnasium as gym
from gymnasium import spaces
import json
import numpy as np
from pathlib import Path
import random

from ..validation.docker_runner import run_code
from ..validation.patch_validator import validate_patch

class SentinelEnv(gym.Env):
    """
    Gymnasium environment for Sentinel-Synth
    """
    metadata = {"render_modes": ["human"]}
    
    ACTION_ANALYZE = 0
    ACTION_EXECUTE_SANDBOX = 1
    ACTION_BLOCK_PR = 2
    ACTION_SUBMIT_PATCH = 3
    ACTION_REQUEST_REVIEW = 4

    def __init__(self, scenarios_path="sentinel_synth/data/scenarios.json", use_docker=False):
        super().__init__()
        
        self.use_docker = use_docker
        self.scenarios_path = scenarios_path
        self.scenarios = self._load_scenarios()
        
        self.current_scenario = None
        self.step_counter = 0
        self.max_steps = 5

        # Define Observation Space
        # text max length 5000 chars
        self.observation_space = spaces.Dict(
            {
                "code_snippet": spaces.Text(max_length=5000, charset="".join(gym.spaces.text.alphanumeric) + " \n\t\r!@#$%^&*()_+-=[]{}|;':\",.<>/?\\"),
                "static_flags": spaces.Box(low=0, high=1, shape=(5,), dtype=np.int32),
                "risk_score": spaces.Box(low=0.0, high=1.0, shape=(1,), dtype=np.float32),
            }
        )

        # Define Action Space
        self.action_space = spaces.Discrete(5)

    def _load_scenarios(self):
        try:
            with open(self.scenarios_path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load scenarios from {self.scenarios_path}: {e}")
            return []

    def _compute_static_flags(self, code_snippet: str):
        flags = np.zeros(5, dtype=np.int32)
        
        if "eval(" in code_snippet or "exec(" in code_snippet:
            flags[0] = 1
        if "subprocess" in code_snippet or "os.system" in code_snippet:
            flags[1] = 1
        if "socket" in code_snippet or "requests" in code_snippet:
            flags[2] = 1
        if "os.environ" in code_snippet:
            flags[3] = 1
        if "base64" in code_snippet or "zlib" in code_snippet:
            flags[4] = 1
            
        return flags

    def _get_obs(self):
        code = self.current_scenario["code_snippet"]
        # truncate code to 5000 chars to fit text space
        if len(code) > 5000:
             code = code[:5000]
        
        flags = self._compute_static_flags(code)
        risk_score = np.array([np.sum(flags) / 5.0], dtype=np.float32)
        
        return {
            "code_snippet": code,
            "static_flags": flags,
            "risk_score": risk_score
        }

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        if not self.scenarios:
             # Fallback if no scenarios to prevent crash
             self.current_scenario = {
                 "id": "fallback", "type": "functional", "label": "benign", 
                 "code_snippet": "print('hello')", "patch": None
             }
        else:
             # We can optionally pass a specific scenario via options
             if options and "scenario" in options:
                 self.current_scenario = options["scenario"]
             else:
                 self.current_scenario = random.choice(self.scenarios)
             
        self.step_counter = 0
        self.last_action = None
        self.last_reward = 0
        
        return self._get_obs(), {}

    def step(self, action):
        self.step_counter += 1
        
        reward = 0
        done = False
        info = {}
        
        self.last_action = action
        
        if action == self.ACTION_ANALYZE:
            # Small exploration reward for analyzing
            reward = 0.05
            info = {"analysis": "Static analysis reveals potential injection points if untrusted input is passed."}
            
        elif action == self.ACTION_EXECUTE_SANDBOX:
            # Execute code snippet
            result = run_code(self.current_scenario["code_snippet"], timeout_sec=3, use_docker=self.use_docker)
            info = {"telemetry": result}
            # Shaped reward for gathering info
            reward = 0.1
            
        elif action == self.ACTION_BLOCK_PR:
            if self.current_scenario["label"] == "malicious":
                reward = 1.5 # Correctly blocked
            else:
                reward = -2.0 # False positive block
            done = True
            
        elif action == self.ACTION_SUBMIT_PATCH:
            scenario_patch = self.current_scenario.get("patch")
            if not scenario_patch:
                if self.current_scenario["label"] == "benign":
                    # Benign code doesn't need a patch, but submitting one is a mistake
                    reward = -1.0
                else:
                    # Should have a patch for malicious, but it's missing in scenario?
                    reward = -0.5
            else:
                success, msg, details = validate_patch(self.current_scenario, scenario_patch, use_docker=self.use_docker)
                info = {"validation_success": success, "msg": msg, "details": details}
                
                if success:
                    if self.current_scenario["label"] == "malicious":
                        reward = 4.0 # High reward for fixing vulnerability
                    else:
                        reward = -2.5 # High penalty for breaking benign code
                else:
                    reward = -1.5 # Patch failed validation
            done = True
            
        elif action == self.ACTION_REQUEST_REVIEW:
            if self.current_scenario["type"] == "false_positive":
                reward = 0.5 # Good choice for ambiguous cases
            else:
                reward = 0.0
            done = True
            info = {"review_requested": True}
            
        # Check max steps
        if self.step_counter >= self.max_steps and not done:
            reward -= 0.5 # Penalty for timeout
            done = True
            
        self.last_reward = reward
        return self._get_obs(), reward, done, False, info

    def render(self):
        print(f"Step: {self.step_counter} | Action: {self.last_action} | Reward: {self.last_reward}")
