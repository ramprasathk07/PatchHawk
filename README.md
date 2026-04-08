# PatchHawk

[![Weights & Biases](https://img.shields.io/badge/Weights%20%26%20Biases-FFBE00?logo=weightsandbiases&logoColor=black)](https://wandb.ai)
[![Hugging Face](https://img.shields.io/badge/Hugging%20Face-FFD21E?logo=huggingface&logoColor=black)](https://huggingface.co)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue?logo=python&logoColor=white)](https://python.org)
[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compliant-2ea44f)](https://openenv.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

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
└── README.md
```

---

## Getting Started

### Prerequisites

- Python 3.12 or higher
- Docker Engine with buildx support
- NVIDIA GPU with 8 GB VRAM or more (required for training; recommended for inference)
- Hugging Face account and access token

### Installation

Clone the repository and install dependencies into a virtual environment.

```bash
git clone https://github.com/ramprasathk07/PatchHawk.git
cd PatchHawk

python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e .
```

### Environment Setup

```bash
cp .env.example .env
# Populate .env with HF_TOKEN, OPENAI_API_KEY, WANDB_API_KEY, and any other required keys.

docker build -t patchhawk-sandbox:latest -f docker/Dockerfile.sandbox .
```

### Running the Agent

Start the environment server and the inference loop in separate terminal sessions.

```bash
# Terminal 1 — environment server
python -m server.app --port 8000

# Terminal 2 — inference loop
python src/envs/patchhawk/inference.py --env-url http://localhost:8000
```

---

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

---

## Reward Rubric

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

```bash
streamlit run patchhawk/app/dashboard.py
```

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

---

## License

Distributed under the MIT License. See `LICENSE` in the repository root for the full terms.

Developed by Ramprasath K and the PatchHawk team.
