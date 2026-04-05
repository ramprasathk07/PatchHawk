"""
Streamlit dashboard for PatchHawk.

Usage:
    streamlit run patchhawk/app/dashboard.py
"""

import json
import os
import sys
import time
from pathlib import Path

import streamlit as st

# Ensure project root is importable when run via `streamlit run`
_project_root = str(Path(__file__).resolve().parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from patchhawk.agent.environment import PatchHawkEnv
from patchhawk.agent.sandbox import validate_patch

# ── Page config ───────────────────────────────────────────────────
st.set_page_config(
    page_title="PatchHawk Dashboard",
    page_icon="🦅",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom styling ────────────────────────────────────────────────
st.markdown("""
<style>
    :root {
        --cobalt: #0047AB;
        --cobalt-light: #2A6DC9;
        --accent-green: #3fb950;
        --accent-red: #ff7b72;
        --accent-blue: #79c0ff;
        --bg-dark: #0d1117;
        --bg-card: #161b22;
        --text-primary: #c9d1d9;
    }
    .stApp { background-color: var(--bg-dark); color: var(--text-primary); }
    h1, h2, h3 { color: #58a6ff !important; }
    .stButton>button {
        background: linear-gradient(135deg, var(--cobalt), var(--cobalt-light));
        color: #fff; border: none; border-radius: 6px;
        font-weight: 600; transition: transform .15s, box-shadow .15s;
    }
    .stButton>button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 14px rgba(42,109,201,.45);
    }
    .info-box {
        background: var(--bg-card); border-left: 4px solid var(--cobalt);
        padding: 1rem; border-radius: 6px; margin-bottom: 1rem;
    }
    .status-malicious { color: var(--accent-red); font-weight: bold; }
    .status-benign    { color: var(--accent-green); font-weight: bold; }
    .status-patched   { color: var(--accent-blue); font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ── Singleton env ─────────────────────────────────────────────────
@st.cache_resource
def get_env():
    return PatchHawkEnv(use_docker=False)


# ── Main ──────────────────────────────────────────────────────────
def main():
    st.title("🦅 PatchHawk | Supply-Chain Guard")
    st.caption(
        "RL-powered vulnerability detection and auto-patching — "
        "OpenEnv Hackathon MVP"
    )

    env = get_env()

    # ── Sidebar ───────────────────────────────────────────────────
    with st.sidebar:
        st.header("⚙️ Control Panel")
        mode = st.radio("Mode", ["Demo Scenarios", "Custom Code"])
        run_docker = st.checkbox("Use Docker Sandbox", value=False)
        st.markdown("---")
        st.markdown("**W&B:** [patchhawk](https://wandb.ai)")
        st.markdown("**Model:** `grpo_lora` (Qwen2.5-Coder-7B)")
        st.markdown("**A2A:** `GET /agent/card`  ·  `POST /agent/act`")

    env.use_docker = run_docker

    # ── Demo scenario loader ──────────────────────────────────────
    if mode == "Demo Scenarios":
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🔴 Load Malicious Example"):
                mal = [s for s in env.scenarios if s.get("label") == "malicious"]
                if mal:
                    st.session_state["code"] = mal[0]["code_snippet"]
                    st.session_state["scenario"] = mal[0]
        with c2:
            if st.button("🟢 Load Benign Example"):
                ben = [s for s in env.scenarios if s.get("label") == "benign"]
                if ben:
                    st.session_state["code"] = ben[0]["code_snippet"]
                    st.session_state["scenario"] = ben[0]

    # ── Code input ────────────────────────────────────────────────
    code_input = st.text_area(
        "Python Code Snippet",
        value=st.session_state.get("code", ""),
        height=280,
    )

    # ── Analyze button ────────────────────────────────────────────
    if st.button("🔍 Analyze"):
        if not code_input.strip():
            st.warning("Paste or load some code first.")
            return

        scenario = st.session_state.get("scenario")
        if (
            mode == "Custom Code"
            or not scenario
            or scenario.get("code_snippet") != code_input
        ):
            scenario = {
                "id": "custom",
                "label": "unknown",
                "type": "custom",
                "code_snippet": code_input,
                "patch": None,
                "unit_test_code": None,
                "attack_type": None,
            }

        with st.spinner("Agent running in OpenEnv…"):
            obs, info = env.reset(options={"scenario": scenario})
            time.sleep(0.4)  # visual feedback

            risk = float(obs["risk_score"][0])

            # Step 1 – Analyze
            obs, r1, _, _, _ = env.step(env.ACTION_ANALYZE)

            # Step 2 – Decide
            if risk > 0.4 and scenario.get("patch"):
                final_action = env.ACTION_SUBMIT_PATCH
            elif risk > 0.6:
                final_action = env.ACTION_BLOCK_PR
            else:
                final_action = env.ACTION_REQUEST_REVIEW

            obs, r2, term, trunc, step_info = env.step(final_action)
            total_reward = r1 + r2

        # ── Results ───────────────────────────────────────────────
        st.subheader("📊 Agent Report")
        m1, m2, m3 = st.columns(3)
        m1.metric("Risk Score", f"{risk:.2f}")
        m2.metric("Decision", env.ACTION_NAMES[final_action])
        m3.metric("Reward", f"{total_reward:+.2f}")

        tab1, tab2, tab3 = st.tabs(["Action Details", "Docker Telemetry", "Patch Proposal"])

        with tab1:
            if final_action == env.ACTION_BLOCK_PR:
                st.markdown(
                    "<div class='info-box status-malicious'>⛔ BLOCKED — "
                    "Vulnerability detected.</div>",
                    unsafe_allow_html=True,
                )
            elif final_action == env.ACTION_SUBMIT_PATCH:
                st.markdown(
                    "<div class='info-box status-patched'>🩹 PATCH SUBMITTED — "
                    "Vulnerability neutralised.</div>",
                    unsafe_allow_html=True,
                )
                val_info = step_info.get("validation", "")
                if val_info:
                    st.info(val_info)
            else:
                st.markdown(
                    "<div class='info-box status-benign'>✅ REVIEW — "
                    "Code appears safe or needs human review.</div>",
                    unsafe_allow_html=True,
                )

        with tab2:
            telem = step_info.get("telemetry")
            if telem:
                st.json(telem)
            else:
                st.info("No sandbox execution for this path.")

        with tab3:
            if final_action == env.ACTION_SUBMIT_PATCH and scenario.get("patch"):
                st.code(scenario["patch"], language="python")

                # Run validation pipeline for display
                ok, msg, details = validate_patch(
                    scenario, scenario["patch"], use_docker=run_docker
                )
                if ok:
                    st.success(f"✅ {msg} — {details.get('validation_log', '')}")
                else:
                    st.error(f"❌ {msg}")
            else:
                st.info("No patch generated for this decision path.")


if __name__ == "__main__":
    main()
