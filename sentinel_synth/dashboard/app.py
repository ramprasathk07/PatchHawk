import streamlit as st
import json
import time

from sentinel_synth.envs.sentinel_env import SentinelEnv

st.set_page_config(
    page_title="Sentinel-Synth Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Cobalt Blue theming and dark mode
st.markdown("""
<style>
    :root {
        --cobalt-blue: #0047AB;
        --cobalt-light: #2A6DC9;
        --cobalt-dark: #002255;
    }
    .stApp {
        background-color: #0d1117;
        color: #c9d1d9;
    }
    .css-1d391kg {
        background-color: #161b22;
    }
    /* Headers */
    h1, h2, h3 {
        color: #58a6ff !important;
    }
    /* Sidebar */
    .css-1lcbmhc {
        background-color: #161b22;
    }
    /* Buttons */
    .stButton>button {
        background-color: var(--cobalt-blue);
        color: white;
        border: none;
        border-radius: 4px;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: var(--cobalt-light);
        border: none;
        color: white;
    }
    /* Info box */
    .info-box {
        background-color: #1c2128;
        border-left: 4px solid var(--cobalt-blue);
        padding: 1rem;
        border-radius: 0.25rem;
        margin-bottom: 1rem;
    }
    
    .status-malicious { color: #ff7b72; font-weight: bold; }
    .status-benign { color: #3fb950; font-weight: bold; }
    .status-patched { color: #79c0ff; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_env():
    return SentinelEnv(use_docker=False)

def main():
    st.title("🛡️ Sentinel-Synth | GRPO DevSecOps Agent")
    st.markdown("Supply-chain attack detection and auto-patching platform via Reinforcement Learning.")

    env = get_env()

    with st.sidebar:
        st.header("Control Panel")
        mode = st.radio("Mode", ["Demo Scenarios", "Custom Code"])
        run_docker = st.checkbox("Use Docker Sandbox", value=False)
        st.markdown("---")
        st.markdown("**W&B Run:** [View Logs](https://wandb.ai)")
        st.markdown("**LLM Adapter:** `grpo_lora_qwen`")
        
    env.use_docker = run_docker

    if mode == "Demo Scenarios":
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Load Malicious Example"):
                malicious = [s for s in env.scenarios if s["label"] == "malicious"]
                if malicious:
                    st.session_state["code"] = malicious[0]["code_snippet"]
                    st.session_state["scenario"] = malicious[0]
                    
        with col2:
            if st.button("Load Benign Example"):
                benign = [s for s in env.scenarios if s["label"] == "benign"]
                if benign:
                    st.session_state["code"] = benign[0]["code_snippet"]
                    st.session_state["scenario"] = benign[0]

    code_input = st.text_area("Python Code Snippet", value=st.session_state.get("code", ""), height=300)

    if st.button("Analyze & Diffuse"):
        if not code_input:
            st.warning("Please provide code to analyze.")
            return

        scenario = st.session_state.get("scenario")
        if mode == "Custom Code" or not scenario or scenario["code_snippet"] != code_input:
            scenario = {
                "id": "custom",
                "label": "unknown", 
                "type": "custom",
                "code_snippet": code_input,
                "patch": None
            }
            
        with st.spinner("Agent computing actions in OpenEnv..."):
            obs, _ = env.reset(options={"scenario": scenario})
            
            # Dummy policy for UI demonstration since we don't load the real adapter here yet
            time.sleep(1)
            risk = obs["risk_score"][0]
            action = env.ACTION_SUBMIT_PATCH if risk > 0.4 and scenario.get("patch") else env.ACTION_ANALYZE
            
            # If merely analyzed, let's step once more to see what we do
            if action == env.ACTION_ANALYZE:
                obs, reward, done, _, info = env.step(action)
                action = env.ACTION_BLOCK_PR if risk > 0.6 else env.ACTION_REQUEST_REVIEW
                
            obs, reward, done, _, info = env.step(action)

        st.subheader("Agent Report")
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Component Risk Score", f"{risk:.2f}", delta_color="inverse", delta=f"{risk-0.2:.2f}")
        action_names = ["ANALYZE", "SANDBOX", "BLOCK", "PATCH", "REVIEW"]
        c2.metric("Agent Action Taken", action_names[action])
        c3.metric("Reward Received", f"{reward:+.2f}")

        # Display tabs for detailed results
        tab1, tab2, tab3 = st.tabs(["Action Details", "Sandbox Telemetry", "Patch Proposal"])
        
        with tab1:
            if action == env.ACTION_BLOCK_PR:
                st.markdown("<div class='info-box status-malicious'>Action: BLOCKED. Vulnerability detected and no patch available.</div>", unsafe_allow_html=True)
            elif action == env.ACTION_SUBMIT_PATCH:
                st.markdown("<div class='info-box status-patched'>Action: PATCH SUBMITTED. Vulnerability neutralized.</div>", unsafe_allow_html=True)
                st.json(info)
            else:
                st.markdown("<div class='info-box status-benign'>Action: REVIEW / ANALYZE. Code appears nominally safe or requires human review.</div>", unsafe_allow_html=True)

        with tab2:
            st.markdown("**(Telemetry simulates background execution for static code)**")
            if "telemetry" in info:
                st.json(info["telemetry"])
            else:
                st.info("No sandbox execution triggered for this path.")
                
        with tab3:
            if action == env.ACTION_SUBMIT_PATCH and scenario.get("patch"):
                st.code(scenario["patch"], language='python')
                if info.get("validation_success"):
                    st.success("Patch passed 3-stage validation pipeline!")
            else:
                st.info("No patch generated.")

if __name__ == "__main__":
    main()
