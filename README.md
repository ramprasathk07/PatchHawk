# 🦅 Sentinel-Synth: Autonomous Supply-Chain Guard

**Sentinel-Synth** is an advanced Reinforcement Learning (RL) platform designed for the detection, analysis, and automated patching of software supply-chain vulnerabilities. It leverages **Group Relative Policy Optimization (GRPO)** and **Meta's Synthetic Data Kit** to train fine-tuned LLM agents that can secure CI/CD pipelines autonomously.

---

## 🏗 System Architecture

The Sentinel-Synth ecosystem is built on four functional pillars:

```mermaid
graph TD
    A[Meta SDK / Mutation Engine] -->|Synthetic Scenarios| B[Scenarios JSON]
    B --> C[Gymnasium RL Environment]
    C -->|Observations| D[GRPO Policy Agent (Qwen2.5-Coder)]
    D -->|Actions| C
    C -->|Validation| E[Docker Sandbox & Patch Validator]
    E -->|Reward Signal| D
    D -->|Metrics| F[W&B / Dashboard]
```

### Core Components
- **`sentinel_synth.data`**: Orchestrates scenario synthesis using Meta's `synthetic-data-kit` (Track A) and a custom mutation engine (Track B).
- **`sentinel_synth.envs`**: A `gymnasium` environment that formalizes DevSecOps tasks into an RL problem.
- **`sentinel_synth.validation`**: A two-tiered execution engine that uses isolated Docker containers for syntax checking and re-attack verification.
- **`sentinel_synth.training`**: The training loop using `trl` and `unsloth` for efficient GRPO fine-tuning.

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+** (3.11 recommended)
- **Docker** (Ensure your user has permission to manage containers)
- **vLLM Server** (Optional, for Track A synthetic data generation)
- **GPU** (NVIDIA/AMD) for standard training; CPU supported for dry-runs.

### 2. Installation
```bash
# Set up a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate

# Install the base system
pip install -r requirements.txt
pip install -e .

# Build the sandbox Docker image
docker build -t sentinel-sandbox:latest -f docker/Dockerfile.sandbox .
```

### 3. Configuration
Copy the sample environment file and adjust your settings:
```bash
cp .env.example .env  # Define model paths, W&B keys, etc.
```
Edit `config.yaml` to tune training hyperparameters and environment thresholds.

---

## 🧪 Detailed Workflow

### 📤 Phase 1: Data Generation & Analysis
Sentinel-Synth generates diverse training scenarios including Typosquatting, Obfuscated Exec, and Subprocess Backdoors.

**Using Meta's Synthetic Data Kit (Track A):**
1. Ensure a vLLM server is running.
2. Configure `sentinel_synth/data/sdk_config.yaml`.
3. Run the generator:
```bash
python3 -m sentinel_synth.data.generate_scenarios --use-sdk --output data/scenarios.json
```

**Using the Mutation Engine (Track B):**
This mode takes benign code and injects malicious patterns deterministically.
```bash
python3 -m sentinel_synth.data.generate_scenarios --output data/scenarios.json
```

---

### 🧠 Phase 2: Agent Training (GRPO)
Train the `Qwen2.5-Coder-7B` model using the novel Group Relative Policy Optimization algorithm. GRPO allows the agent to learn complex decision-making without a value model.

**Dry-Run (Pipeline Validation):**
Test the logic on CPU without a GPU:
```bash
python3 -m sentinel_synth.training.train_grpo --dry-run
```

**Full Training:**
```bash
# Ensure WANDB is logged in or API key is in .env
python3 -m sentinel_synth.training.train_grpo --use-docker
```
*The agent receives rewards based on: valid detection (+1.5), successful patching (+4.0), and avoiding false positives (-2.0).*

---

### 🛡 Phase 3: Validation & Sandbox Execution
Every patch proposed by the agent is autonomously validated in a secure Docker sandbox:
1. **Syntax Check**: Ensuring the code is parseable.
2. **Functional Test**: Running units tests from `scenarios.json`.
3. **Re-Attack Verification**: The system re-executes the vulnerability payload to verify the patch actually neutralized the threat (e.g., checking if suspicious file writes or network calls stopped).

---

## 📊 Monitoring & UI
- **Weights & Biases**: Real-time tracking of mean rewards, action distributions, and loss curves.
- **Streamlit Dashboard**: A professional interface for interactive analysis:
```bash
streamlit run sentinel_synth/dashboard/app.py
```

---

## 📄 License
Sentinel-Synth is licensed under the Apache 2.0 License. See the LICENSE file for details.