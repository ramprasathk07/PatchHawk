# 🦅 PatchHawk: Autonomous Supply-Chain Guard

[![W&B](https://img.shields.io/badge/W%26B-patchhawk-blue?logo=weightsandbiases)](https://wandb.ai/ramprasathk07/patchhawk)
[![HuggingFace](https://img.shields.io/badge/🤗_Model-patchhawk-yellow)](https://huggingface.co/ramprasathk07/patchhawk)
[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://python.org)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-Hackathon_Finalist-orange)](https://github.com/pytorch/openenv)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

> **PatchHawk is an state-of-the-art autonomous DevSecOps agent powered by Group Relative Policy Optimization (GRPO). It goes beyond detection by validating vulnerabilities in isolated Docker sandboxes and generating verified, syntax-correct patches.**

---

## 📽️ The Vision: Cyber-Physical RL Loop

Traditional security scanners often produce high signal-to-noise ratios and "hallucinated" vulnerabilities. PatchHawk bridges this gap by implementing a **Cyber-Physical Reinforcement Learning Loop**, where the model's reward is tied to the actual execution success of its patches in a real environment.

```mermaid
graph TD
    A[Source Code / PR] --> B{PatchHawk Agent}
    B -->|Analyze| C[Static Analysis]
    B -->|Test| D[Docker Sandbox]
    D -->|Detonate| E[Behavioral Telemetry]
    E --> F[Reward Signal]
    B -->|Patch| G[Verification Pipeline]
    G -->|Syntax Check| H{Success?}
    G -->|Unit Tests| I{Pass?}
    G -->|Re-Attack| J{Defeated?}
    H & I & J -->|All Pass| K[Positive Reward +3.0]
    H | I | J -->|Failure| L[Negative Penalty -1.5]
    K --> M[Model Update/Optimization]
```

---

## ✨ Key Features

-   🛡️ **Autonomous Detection**: Sophisticated analysis of supply-chain vectors (typosquatting, backdoors, exfiltration).
-   🐳 **Hardened Sandboxing**: High-fidelity Docker isolation with zero-network access and strict resource caps.
-   🧠 **GRPO-Driven Learning**: Uses Group Relative Policy Optimization (DeepSeek-R1 style) for reasoning and trial-and-error mastery.
-   🧩 **XML Reasoning**: Enforces a structured `<thought>...</thought>` chain for transparent decision-making.
-   📊 **SOC Dashboard**: Real-time Streamlit interface for auditing agent behavior and reward telemetry.
-   ✅ **OpenEnv Compliant**: Fully integrated with the [PyTorch OpenEnv](https://github.com/pytorch/openenv) framework.

---

## 🛠 Project Structure

The codebase is organized into modular components for training, inference, and environment simulation.

```text
PatchHawk/
├── src/envs/patchhawk/    # 📦 Core OpenEnv Submission Package
│   ├── server/            # FastAPI environment server
│   ├── models.py          # Type-safe contract definitions
│   ├── client.py          # Environment interaction client
│   └── inference.py       # Main agent execution loop
├── patchhawk/             # 🧠 Logic & Training
│   ├── data/              # Scenario generation & datasets
│   ├── training/          # GRPO/Unsloth training scripts
│   └── app/               # Streamlit SOC Dashboard
├── docker/                # 🐳 Container configurations
├── config.yaml            # Environment & Agent configuration
└── openenv.yaml           # OpenEnv metadata
```

---

## 🚀 Getting Started

### Prerequisites

-   **Python 3.12+**
-   **Docker Engine** (running locally)
-   **Nvidia GPU** (8GB+ VRAM recommended for local training/inference)

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/ramprasathk07/PatchHawk.git
cd PatchHawk

# Create virtual environment and install core dependencies
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Environment Setup

```bash
# Setup environment variables
cp .env.example .env
# Edit .env to include your HF_TOKEN and OpenAI/Anthropic keys

# Build the validation sandbox
docker build -t patchhawk-sandbox:latest -f docker/Dockerfile.sandbox .
```

### 3. Running the Agent (Dry Run)

```bash
# Start the environment server
python -m server.app --port 8000

# Execute the inference loop
python src/envs/patchhawk/inference.py --env-url http://localhost:8000
```

---

## 💎 Reward Rubric (Action Space)

PatchHawk implements a granular scoring system to guide the agent toward safe and effective decisions.

| Action ID | Action Name | Base Reward | Success Criteria |
| :--- | :--- | :--- | :--- |
| **0** | `ANALYZE` | `0.0` | Observation step; used for data gathering. |
| **1** | `DETONATE` | `+0.1` | Successfully extract telemetry from Docker. |
| **2** | `BLOCK_PR` | `+2.0 / -1.0` | Rewarded for malware; penalized for False Positives. |
| **3** | `SUBMIT_PATCH` | `+3.0 / -1.5` | **The Goal.** Requires pass in Syntax -> Test -> Re-Attack. |
| **4** | `ESCALATE` | `0.0` | Hand off to human expert if uncertainty is high. |

### Dynamic Scaling
-   **Risk Accuracy**: Agent receives up to `+2.0` bonus for predicting the exact risk score.
-   **Safety Multiplier**: Frequent failed syntax checks trigger a decay factor on all rewards.

---

## 📈 Dashboard & UI

Launch the **Security Operations Center (SOC)** to watch the agent reason in real-time.

```bash
streamlit run patchhawk/app/dashboard.py
```

-   **Terminal Trace**: Live XML reasoning logs.
-   **Docker Monitor**: Real-time stdout/stderr from the sandbox.
-   **Reward Audit**: Detailed breakdown of why specific points were awarded.

---

## 🗺️ Roadmap

-   [ ] **Multi-Agent Coordination**: Deploying "Attacker" vs "Defender" models for automated red-teaming.
-   [ ] **CVE Ingestion**: Automated generation of training scenarios from current NVD databases.
-   [ ] **Cross-Language Support**: Expanding beyond Python to Go, Javascript, and Rust.
-   [ ] **Kubernetes Native**: Orchestrating sandboxes at scale using K8s instead of local Docker.

---

## 📝 License

Distributed under the **MIT License**. See `LICENSE` or the project root for more information.

Developed with ❤️ by **Ramprasath K & The PatchHawk Team**
Ramprasath K & The PatchHawk Team