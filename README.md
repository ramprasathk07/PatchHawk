---
title: PatchHawk
emoji: 🦅
colorFrom: gray
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# 🦅 PatchHawk: Autonomous Supply-Chain Guard

[![Weights & Biases](https://img.shields.io/badge/Weights%20%26%20Biases-FFBE00?logo=weightsandbiases&logoColor=black)](https://wandb.ai)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compliant-2ea44f)](https://openenv.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Built for the OpenEnv Hackathon 2026 by Meta**

PatchHawk is an autonomous DevSecOps agent powered by Group Relative Policy Optimization (GRPO). It moves beyond static vulnerability detection by validating findings inside isolated Docker sandboxes and generating verified, syntactically correct patches. The system closes the loop between detection, validation, and remediation through a cyber‑physical reinforcement learning feedback cycle.

---

## 📽️ The Vision: Cyber‑Physical RL Loop

Traditional security scanners suffer from high false‑positive rates and often report vulnerabilities that cannot be exploited or fixed in practice. PatchHawk addresses this by implementing a reinforcement learning loop where the model's reward is tied directly to the success of its patches inside a real execution environment.

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
    G -->|Re‑Attack| J{Defeated?}
    H & I & J -->|All Pass| K[Positive Reward +3.0]
    H | I | J -->|Failure| L[Negative Penalty -1.5]
    K --> M[Model Update / Optimization]
    L --> M
```

The agent learns to produce patches that not only compile but also withstand re‑execution of the original exploit vector.

---

## ✨ Key Features

-   🛡️ **Autonomous Detection**: Sophisticated supply‑chain analysis identifying typosquatting, backdoors, data exfiltration, and malicious logic in dependencies.
-   🐳 **Hardened Sandboxing**: High‑fidelity Docker isolation with network‑disabled execution, strict resource caps, and ephemeral file systems to safely detonate suspicious code.
-   🧠 **GRPO‑Driven Learning**: Group Relative Policy Optimization (inspired by DeepSeek‑R1) enables trial‑and‑error mastery and structured reasoning without a separate critic model.
-   🧩 **XML Reasoning Traces**: All agent decisions are accompanied by a machine‑readable `<thought>...</thought>` block, providing full auditability of the decision‑making process.
-   📊 **SOC Dashboard**: Real‑time Streamlit interface for monitoring agent behavior, sandbox telemetry, and reward breakdowns.
-   ✅ **OpenEnv Compliance**: Fully integrated with the PyTorch OpenEnv framework, ensuring reproducible and shareable reinforcement learning environments.

---

## 🛠️ Project Structure

```text
PatchHawk/
├── src/envs/patchhawk/    # 📦 OpenEnv Submission Package
│   ├── server/            # FastAPI environment server
│   ├── models.py          # Type‑safe contract definitions
│   ├── client.py          # Environment interaction client
│   └── inference.py       # Main agent execution loop
├── patchhawk/             # 🧠 Core Logic & Training
│   ├── data/              # Scenario generation & datasets
│   ├── training/          # GRPO / Unsloth training scripts
│   └── app/               # Streamlit SOC Dashboard
├── docker/                # 🐳 Container configurations
├── config.yaml            # Environment & Agent configuration
├── openenv.yaml           # OpenEnv metadata
├── .env.example           # Environment variable template
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

-   Python 3.12 or higher
-   Docker Engine (running locally, with buildx available)
-   NVIDIA GPU (8 GB VRAM or more recommended for training and inference)
-   Hugging Face account and token (for model access)

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/ramprasathk07/PatchHawk.git
cd PatchHawk

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate

# Install core dependencies
pip install -e .
```

### 2. Environment Setup

```bash
# Copy the environment template and populate your keys
cp .env.example .env
# Edit .env to include HF_TOKEN, OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.

# Build the validation sandbox Docker image
docker build -t patchhawk-sandbox:latest -f docker/Dockerfile.sandbox .
```

### 3. Running the Agent (Dry Run)

```bash
# Start the environment server (in one terminal)
python -m server.app --port 8000

# Execute the inference loop (in another terminal)
python src/envs/patchhawk/inference.py --env-url http://localhost:8000
```

---

## 💎 Reward Rubric

The agent is guided by a granular reward structure that encourages safe, effective, and verifiable actions.

| Action ID | Action Name | Base Reward | Success Criteria |
| :--- | :--- | :--- | :--- |
| **0** | `ANALYZE` | `0.0` | Observation step; used solely for data gathering. |
| **1** | `DETONATE` | `+0.1` | Successfully extract telemetry from the Docker sandbox. |
| **2** | `BLOCK_PR` | `+2.0 / -1.0` | Positive reward when correctly blocking a malicious PR; negative penalty for false positives. |
| **3** | `SUBMIT_PATCH` | `+3.0 / -1.5` | The primary goal. Reward requires passing syntax check, unit tests, and a re‑attack validation. |
| **4** | `ESCALATE` | `0.0` | Hands off to a human expert when uncertainty exceeds a configurable threshold. |

### Dynamic Scaling Factors
-   **Risk Accuracy Bonus**: Up to `+2.0` additional reward for accurately predicting the risk score of a vulnerability.
-   **Safety Multiplier**: Repeated syntax check failures apply a decay factor to all future rewards.

---

## 📈 Dashboard & UI

Launch the **Security Operations Center (SOC)** dashboard to observe the agent's reasoning in real time.

```bash
streamlit run patchhawk/app/dashboard.py
```

The dashboard provides:
-   Live XML reasoning logs from the agent.
-   Real‑time stdout/stderr streams from the Docker sandbox.
-   Detailed audit trail of reward assignments and verification outcomes.

---

## 🗺️ Roadmap & Future Work

-   [ ] **Multi‑Agent Coordination**: Deploy attacker and defender models for automated red‑teaming exercises.
-   [ ] **CVE Ingestion**: Automatically generate training scenarios from the National Vulnerability Database (NVD).
-   [ ] **Cross-Language Support**: Expand beyond Python to Go, JavaScript, Rust, and Java.
-   [ ] **Kubernetes Native**: Orchestrate sandboxes at scale using Kubernetes instead of local Docker.
-   [ ] **Fine‑Tuned Vulnerability Model**: Train a specialized 7B parameter LLM (e.g., VulnLLM‑R) on vulnerability‑fixing commits.
-   [ ] **Context‑Aware Analysis**: Integrate Code Property Graph (CPG) slicing for LLM‑based semantic vulnerability detection.
-   [ ] **Silent Patch Detection**: Identify security‑relevant commits that were not publicly disclosed.
-   [ ] **AI‑Generated Code Audit**: Trace vulnerabilities back to AI coding assistants (e.g., GitHub Copilot, ChatGPT).
-   [ ] **Automated PR Remediation**: Generate and submit fix‑containing pull requests for detected vulnerabilities.
-   [ ] **Adversarial Training Loop**: Implement a self‑improving LLM‑vs‑LLM red‑team / blue‑team training regimen.
-   [ ] **Supply‑Chain Malware Detection**: Extend dependency analysis to identify novel, unpublished attack patterns.

---

## 📝 License

Distributed under the **MIT License**. See the LICENSE file in the repository root for full details.

Developed with ❤️ by **Ramprasath K & The PatchHawk Team** for the OpenEnv Hackathon 2026 hosted by Meta.