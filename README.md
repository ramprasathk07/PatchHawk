# 🦅 PatchHawk: Autonomous Supply-Chain Guard

[![W&B](https://img.shields.io/badge/W%26B-patchhawk-blue?logo=weightsandbiases)](https://wandb.ai/ramprasathk07/patchhawk)
[![HuggingFace](https://img.shields.io/badge/🤗_Model-patchhawk-yellow)](https://huggingface.co/ramprasathk07/patchhawk)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-Hackathon_Finalist-orange)](https://github.com/pytorch/openenv)

> **PatchHawk is an autonomous DevSecOps agent powered by Group Relative Policy Optimization (GRPO). It doesn't just detect vulnerabilities; it validates them in isolated containers and generates verified patches.**

---

## 🚀 The Approach: Cyber-Physical RL Loop

Most security LLMs suffer from "hallucinated security"—they claim a bug is fixed without ever running the code. PatchHawk solves this by implementing a **Cyber-Physical Reinforcement Learning Loop**:

1.  **Detection**: The agent analyzes code snippets for supply-chain attacks (typosquatting, backdoors, exfiltration).
2.  **Simulation**: The agent can choose to "Detonate" suspicious code in a hardened **Docker Sandbox** to observe real syscalls and network behavior.
3.  **Correction**: If malicious, the agent generates a Python patch.
4.  **Verification**: The environment automatically runs the patch through a 3-stage validation (Syntax -> Unit Tests -> Re-Attack Detonation) inside Docker.
5.  **Reward**: The model is rewarded only if the patch **natively passes** all stages.

---

## 🧠 Training Style: GRPO (Group Relative Policy Optimization)

PatchHawk uses **GRPO**, the same technique used in DeepSeek-R1, to train our security agent via trial and error.

-   **Trial & Error**: The model is tasked with fixing complex vulnerabilities. It generates multiple attempts (Groups) for the same problem.
-   **XML Reasoning**: The model is trained to use absolute XML structure:
    ```xml
    <thought>Analyze the base64 encoded string... it is a reverse shell.</thought>
    <risk_score>0.98</risk_score>
    <action>3</action>
    <patch>import os...</patch>
    ```
-   **Relative Scoring**: Instead of using a static "Teacher" model, PatchHawk compares the scores of the 4 attempts against each other. It learns that the attempt that passed the **Docker Syntax Check** is superior to the one that didn't.

---

## 🛠 Action Space & Scoring Rubric (0.0 to 1.0 Evaluator)

The environment manages a complex reward system to move beyond sparse "win/loss" signals.

| Action ID | Action Name | Reward (Base) | Logic |
| :--- | :--- | :--- | :--- |
| **0** | **ANALYZE** | `0.0` | "Do nothing/Observe". Optimal for benign code. |
| **1** | **EXECUTE_SANDBOX** | `+0.1` | Safely detonate payload in Docker and extract telemetry. |
| **2** | **BLOCK_PR** | `+2.0 / -1.0` | Reject PR. Heavily rewarded for malware, penalized for False Positives. |
| **3** | **SUBMIT_PATCH** | **+3.0 / -1.5** | **The Goal.** Reward requires a clean run in the Docker Sandbox. |
| **4** | **REQUEST_REVIEW** | `0.0` | Escalate to a human expert. |

### 💎 Dynamic Bonuses
*   **Risk Accuracy Bonus (+2.0)**: The agent earns a reward of `(1.0 - abs(actual - predicted)) * 2.0`. This ensures it learns to accurately classify risk even if it doesn't take the aggressive patch action.
*   **Safety Penalty (-1.0)**: Any patch that fails a Docker syntax check or units tests results in a heavy penalty to discourage "lazy packaging".

---

## 🐳 Docker Usage & Security

PatchHawk requires a local Docker daemon. The sandbox is strictly isolated:
-   **No Network**: Containers run with `--network none`.
-   **Resource Caps**: Limited to `256MB RAM` and `0.5 CPU` cores.
-   **Non-Root**: Tasks execute as a limited-privilege user.
-   **Validation**: The 3-stage pipeline checks:
    1.  `py_compile`: Does the patch even run?
    2.  `pytest`: Does it break existing functionality?
    3.  `Re-Attack`: If we run the original exploit, does the new patch stop it?

---

## 📁 Installation

```bash
# 1. Clone & Install
git clone https://github.com/ramprasathk07/PatchHawk.git
cd PatchHawk
pip install -r requirements.txt

# 2. Setup Environment
cp .env.example .env
# Fill in HF_TOKEN for local LLM fallback

# 3. Build the Validator Box
docker build -t patchhawk-sandbox:latest -f docker/Dockerfile.sandbox .

# 4. Generate the Training Dataset (1,500 samples)
python -m patchhawk.data.generate_scenarios --num-samples 1500
```

---

## 📈 Dashboard & UI

Launch the **Security Operations Center (SOC)** to watch the agent work in real-time:

```bash
streamlit run patchhawk/app/dashboard.py
```

Features:
- **Terminal Trace**: See the raw thought process (XML/JSON) of the agent.
- **Docker Telemetry**: View real-time output from the sandbox validation.
- **Reward Signal**: Audit why the agent earned (+/-) rewards for its specific decision.

---

## 📝 License
MIT © Ramprasath K & The PatchHawk Team