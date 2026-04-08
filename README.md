# PatchHawk

[![Weights & Biases](https://img.shields.io/badge/Weights%20%26%20Biases-FFBE00?logo=weightsandbiases&logoColor=black)](https://wandb.ai)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compliant-2ea44f)](https://openenv.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<<<<<<< HEAD
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
=======
**Submitted to the OpenEnv Hackathon 2026 — hosted by Meta.**

PatchHawk is an autonomous DevSecOps agent trained with Group Relative Policy Optimization (GRPO). It moves beyond static vulnerability detection by validating findings inside isolated Docker sandboxes and generating syntactically correct, re-attack-verified patches. The system closes the loop between detection, validation, and remediation through a reinforcement learning feedback cycle grounded in real execution environments.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Key Capabilities](#key-capabilities)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Environment Setup](#environment-setup)
  - [Running the Agent](#running-the-agent)
- [Training](#training)
- [Reward Rubric](#reward-rubric)
- [Dashboard](#dashboard)
- [Roadmap](#roadmap)
- [License](#license)

---

## Architecture Overview

Traditional security scanners suffer from high false-positive rates and produce findings that are often unexploitable or unfixable in practice. PatchHawk addresses this through a reinforcement learning loop in which the agent's reward is tied directly to the outcome of its patches inside a live execution environment.

```
Source Code / PR
       |
       v
 PatchHawk Agent
  /      |      \
Analyze  Test  Patch
         |       |
    Docker     Verification
    Sandbox    Pipeline
         |       |
   Behavioral  Syntax Check
   Telemetry   Unit Tests
         |     Re-Attack
          \     /
        Reward Signal
             |
        Model Update
```

The agent learns to produce patches that not only compile but also withstand re-execution of the original exploit vector. Every decision is accompanied by a structured `<thought>` block, providing a complete and machine-readable audit trail.

---

## Key Capabilities

**Autonomous Detection**
Comprehensive supply-chain analysis targeting typosquatting, backdoors, data exfiltration payloads, and malicious dependency logic.
>>>>>>> 05e09d6e3aa6dfea454f54a20062bd90863a8b86

**Hardened Sandboxing**
Docker-based isolation with network-disabled execution, strict resource caps, and ephemeral file systems for safe detonation of suspicious packages.

**GRPO-Driven Learning**
Group Relative Policy Optimization, drawing from the DeepSeek-R1 methodology, enables structured trial-and-error mastery without requiring a separate critic model.

**Structured Reasoning Traces**
All agent actions are accompanied by a `<thought>...</thought>` XML block logged for full decision auditability.

**SOC Dashboard**
Real-time Streamlit interface displaying agent reasoning, sandbox telemetry, and reward breakdowns by action type.

**OpenEnv Compliance**
Fully integrated with the PyTorch OpenEnv framework, ensuring reproducible and shareable reinforcement learning environments.

---

## Project Structure

```
PatchHawk/
<<<<<<< HEAD
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
=======
├── src/
│   └── envs/
│       └── patchhawk/
│           ├── server/          # FastAPI environment server
│           ├── models.py        # Type-safe contract definitions
│           ├── client.py        # Environment interaction client
│           └── inference.py     # Agent execution loop
├── patchhawk/
│   ├── data/                    # Scenario generation and datasets
│   ├── training/                # GRPO training scripts
│   └── app/                     # Streamlit SOC Dashboard
├── docker/
│   └── Dockerfile.sandbox       # Sandbox container configuration
├── config.yaml                  # Environment and agent configuration
├── openenv.yaml                 # OpenEnv metadata
├── .env.example                 # Environment variable template
>>>>>>> 05e09d6e3aa6dfea454f54a20062bd90863a8b86
└── README.md
```

---

## Getting Started

### Prerequisites

<<<<<<< HEAD
-   Python 3.12 or higher
-   Docker Engine (running locally, with buildx available)
-   NVIDIA GPU (8 GB VRAM or more recommended for training and inference)
-   Hugging Face account and token (for model access)
=======
- Python 3.12 or higher
- Docker Engine with buildx support
- NVIDIA GPU with 8 GB VRAM or more (required for training; recommended for inference)
- Hugging Face account and access token
>>>>>>> 05e09d6e3aa6dfea454f54a20062bd90863a8b86

### Installation

Clone the repository and install dependencies into a virtual environment.

```bash
git clone https://github.com/ramprasathk07/PatchHawk.git
cd PatchHawk

<<<<<<< HEAD
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate      # On Windows: .venv\Scripts\activate

# Install core dependencies
=======
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

>>>>>>> 05e09d6e3aa6dfea454f54a20062bd90863a8b86
pip install -e .
```

### Environment Setup

```bash
<<<<<<< HEAD
# Copy the environment template and populate your keys
cp .env.example .env
# Edit .env to include HF_TOKEN, OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.

# Build the validation sandbox Docker image
=======
cp .env.example .env
# Populate .env with HF_TOKEN, OPENAI_API_KEY, WANDB_API_KEY, and any other required keys.

>>>>>>> 05e09d6e3aa6dfea454f54a20062bd90863a8b86
docker build -t patchhawk-sandbox:latest -f docker/Dockerfile.sandbox .
```

### Running the Agent

Start the environment server and the inference loop in separate terminal sessions.

```bash
<<<<<<< HEAD
# Start the environment server (in one terminal)
python -m server.app --port 8000

# Execute the inference loop (in another terminal)
=======
# Terminal 1 — environment server
python -m server.app --port 8000

# Terminal 2 — inference loop
>>>>>>> 05e09d6e3aa6dfea454f54a20062bd90863a8b86
python src/envs/patchhawk/inference.py --env-url http://localhost:8000
```

---

<<<<<<< HEAD
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
=======
## Training

PatchHawk uses GRPO with a 4-bit quantised Qwen2.5-Coder-7B-Instruct base model and LoRA adapters. The training script is located at `patchhawk/training/train_grpo.py`.

**Dependencies**

```bash
pip install trl==1.0.0 peft bitsandbytes accelerate transformers datasets wandb
```

**Dry run (CPU, no model required)**

```bash
python -m patchhawk.training.train_grpo --dry-run
```

**GPU training (RTX 3060 12 GB defaults)**

```bash
python -m patchhawk.training.train_grpo \
    --epochs 3 \
    --batch-size 1 \
    --grad-accum 8 \
    --group-size 4 \
    --max-seq-len 1024 \
    --output-dir grpo_lora
```

Key training parameters and their recommended values for a 12 GB GPU are documented inline in `train_grpo.py`. To upload the trained adapter to the Hugging Face Hub, set the `HF_REPO` environment variable before running.
>>>>>>> 05e09d6e3aa6dfea454f54a20062bd90863a8b86

---

## Reward Rubric

<<<<<<< HEAD
Launch the **Security Operations Center (SOC)** dashboard to observe the agent's reasoning in real time.
=======
The agent is guided by a granular reward structure that incentivises safe, effective, and verifiable actions.

| Action ID | Action Name    | Base Reward  | Success Criteria |
|-----------|----------------|--------------|------------------|
| 0         | ANALYZE        | 0.0          | Observation step; used for data gathering only. |
| 1         | DETONATE       | +0.1         | Successful telemetry extraction from the Docker sandbox. |
| 2         | BLOCK\_PR      | +2.0 / -1.0  | Positive reward for correctly blocking a malicious PR; penalty for false positives. |
| 3         | SUBMIT\_PATCH  | +3.0 / -1.5  | Reward requires passing syntax check, unit tests, and re-attack validation. |
| 4         | ESCALATE       | 0.0          | Defers to a human expert when uncertainty exceeds a configurable threshold. |

**Dynamic Scaling Factors**

- **Risk Accuracy Bonus.** Up to +2.0 additional reward for accurately predicting the risk score of a detected vulnerability.
- **Safety Multiplier.** Repeated syntax check failures apply a cumulative decay factor to all future rewards within a training episode.

---

## Dashboard

Launch the Security Operations Centre dashboard to monitor the agent in real time.
>>>>>>> 05e09d6e3aa6dfea454f54a20062bd90863a8b86

```bash
streamlit run patchhawk/app/dashboard.py
```

<<<<<<< HEAD
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
=======
The dashboard exposes the following views:

- Live structured reasoning logs (`<thought>` traces) from the agent.
- Real-time stdout and stderr streams from the Docker sandbox.
- Detailed audit trail of reward assignments and verification outcomes per episode.

---

## Roadmap

The following capabilities are planned for future releases. Contributions and issue reports are welcome.

- **Multi-Agent Red-Teaming.** Deploy attacker and defender models for automated adversarial exercises.
- **CVE Ingestion.** Automatically generate training scenarios from the National Vulnerability Database.
- **Cross-Language Support.** Extend analysis beyond Python to Go, JavaScript, Rust, and Java.
- **Kubernetes Orchestration.** Scale sandbox execution using Kubernetes instead of local Docker.
- **Fine-Tuned Vulnerability Model.** Train a specialised model on vulnerability-fixing commits.
- **Code Property Graph Integration.** Apply CPG slicing for semantic vulnerability detection.
- **Silent Patch Detection.** Identify security-relevant commits that were not publicly disclosed.
- **AI-Generated Code Audit.** Trace vulnerabilities to AI coding assistants such as GitHub Copilot.
- **Automated PR Remediation.** Generate and submit fix-containing pull requests for detected issues.
- **Adversarial Self-Improvement.** Implement an LLM-vs-LLM red-team / blue-team training regimen.
- **Supply-Chain Malware Detection.** Extend dependency analysis to novel, unpublished attack patterns.
- **Dashboard Enhancements.** Add historical trend analysis, model performance metrics, and alerting.
>>>>>>> 05e09d6e3aa6dfea454f54a20062bd90863a8b86

---

## License

<<<<<<< HEAD
Distributed under the **MIT License**. See the LICENSE file in the repository root for full details.

Developed with ❤️ by **Ramprasath K & The PatchHawk Team** for the OpenEnv Hackathon 2026 hosted by Meta.
=======
Distributed under the MIT License. See `LICENSE` in the repository root for the full terms.

Developed by Ramprasath K and the PatchHawk team.
>>>>>>> 05e09d6e3aa6dfea454f54a20062bd90863a8b86
