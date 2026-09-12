import streamlit as st
import os
from agent.base_agent import Agent

# Ensure demo directory exists for live file uploads
os.makedirs("demo_pages", exist_ok=True)

st.set_page_config(
    page_title="AI Agent Security Gateway",
    page_icon="🐬",
    layout="centered",
    initial_sidebar_state="expanded",
)

# Custom styling matching the clean macOS-style interface
st.markdown(
    """
<style>
    /* Global layout & background */
    .stApp {
        background-color: #f8f9fa;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 6rem;
        max-width: 860px;
    }
    
    /* Header removal */
    header[data-testid="stHeader"] {
        display: none;
    }

    /* Sidebar container */
    [data-testid="stSidebar"] {
        background-color: #f1f3f5 !important;
        border-right: 1px solid #e2e8f0;
        padding-top: 1rem;
    }

    /* macOS Window Controls */
    .mac-window-controls {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 1.2rem;
    }
    .mac-dot {
        width: 11px;
        height: 11px;
        border-radius: 50%;
        display: inline-block;
    }
    .dot-close { background-color: #ff5f56; }
    .dot-min { background-color: #ffbd2e; }
    .dot-expand { background-color: #27c93f; }

    /* Recent Chat cards */
    .chat-card {
        background: #ffffff;
        border-radius: 12px;
        padding: 10px 14px;
        margin-bottom: 8px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
    .chat-card-title {
        font-size: 0.82rem;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 2px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .chat-card-badge {
        font-size: 0.70rem;
        color: #64748b;
    }

    /* Hero section */
    .hero-title {
        font-size: 2.2rem;
        font-weight: 800;
        color: #0f172a;
        margin-top: 8px;
        margin-bottom: 10px;
    }

    .hero-desc {
        font-size: 0.94rem;
        color: #475569;
        line-height: 1.6;
        margin-bottom: 30px;
    }

    /* User Profile Bar */
    .user-profile-chip {
        display: flex;
        align-items: center;
        gap: 10px;
        background: #ffffff;
        padding: 8px 12px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        margin-top: 1.5rem;
    }
    .avatar-circle {
        width: 28px;
        height: 28px;
        border-radius: 50%;
        background-color: #e11d48;
    }

    /* Floating Chat Input styling */
    [data-testid="stChatInput"] {
        background-color: #ffffff;
        border-radius: 28px !important;
        border: 1px solid #cbd5e1 !important;
        box-shadow: 0 4px 16px rgba(0,0,0,0.06) !important;
        padding-left: 10px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────────────────────
# STATE MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chats" not in st.session_state:
    st.session_state.chats = [
        {"title": "Read and summarize demo...", "risk": "100% Intercepted (Tier 1)"},
        {"title": "Check database status", "risk": "0.0% Benign Safe"},
        {"title": "Calculate cost total", "risk": "0.0% Benign Safe"},
    ]

# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        """
    <div class="mac-window-controls">
        <span class="mac-dot dot-close"></span>
        <span class="mac-dot dot-min"></span>
        <span class="mac-dot dot-expand"></span>
        <span style="font-size: 0.78rem; font-weight: 600; color: #3b82f6; margin-left: 6px; text-decoration: underline;">My chats</span>
    </div>
    <div style="font-size: 0.8rem; font-weight: 700; color: #475569; margin-bottom: 12px;">🕒 Recent Chats</div>
    """,
        unsafe_allow_html=True,
    )

    for chat in st.session_state.chats:
        st.markdown(
            f"""
        <div class="chat-card">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <div style="overflow: hidden; max-width: 85%;">
                    <div class="chat-card-title">{chat['title']}</div>
                    <div class="chat-card-badge">{chat['risk']}</div>
                </div>
                <div style="color:#94a3b8; font-size:0.8rem;">🗑️</div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='margin: 16px 0; border: 0; border-top: 1px solid #e2e8f0;'>", unsafe_allow_html=True)

    # Dynamic File Upload Section for Live Demonstrations
    st.markdown("<div style='font-size: 0.8rem; font-weight: 700; color: #475569; margin-bottom: 8px;'>📄 Upload Demo Payload</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload custom poisoned HTML/TXT", label_visibility="collapsed")
    if uploaded_file:
        file_path = os.path.join("demo_pages", uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.success(f"Ready: `demo_pages/{uploaded_file.name}`")
        st.caption("Instruct the agent: 'Read and summarize demo_pages/" + uploaded_file.name + "'")

    st.markdown(
        """
    <div class="user-profile-chip">
        <div class="avatar-circle"></div>
        <div>
            <div style="font-size:0.85rem; font-weight:600; color:#1e293b;">Security Analyst</div>
            <div style="font-size:0.7rem; color:#64748b;">Defense Operations</div>
        </div>
        <div style="margin-left:auto; color:#94a3b8; font-size:0.9rem;">⚙️</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# ─────────────────────────────────────────────────────────────────────────────
# MAIN PANEL
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.messages:
    st.markdown(
        """
    <div style="text-align: left; padding-top: 20px;">
        <div style="font-size: 3.5rem; margin-bottom: -10px;">🐬</div>
        <div class="hero-title">Live Security Gateway</div>
        <div class="hero-desc">
            Chat with your agent while every interaction is analyzed in real time.
            Behind the scenes, actions pass through a 3-tier firewall: <strong>Tier 0</strong> honeytoken canaries,
            <strong>Tier 1</strong> autoencoder trajectory killswitch, and <strong>Tier 2</strong> semantic audit.
            Legitimate multi-tool workflows are preserved while exfiltration and indirect injection are neutralized.
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

# Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "alert" in msg and msg["alert"]:
            if "Tier 0" in msg["alert"] or "Tier 1" in msg["alert"]:
                st.error(msg["alert"])
            else:
                st.warning(msg["alert"])

        if "trace" in msg and msg["trace"]:
            with st.expander("🛡️ Firewall Inspection Trace"):
                for step in msg["trace"]:
                    st.markdown(f"**Step {step.get('step')} — Tool:** `{step.get('tool') or 'FINAL_ANSWER'}`")
                    if step.get("reasoning"):
                        st.caption(f"Reasoning: {step.get('reasoning')}")
                    st.json(step.get("input") or {})
                    st.code(step.get("output") or "No output")

# ─────────────────────────────────────────────────────────────────────────────
# CHAT EXECUTION FLOW
# ─────────────────────────────────────────────────────────────────────────────
user_prompt = st.chat_input("Fetch me the weekly earning data of GOOG or read a document...")

if user_prompt:
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    st.rerun()

if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    latest_prompt = st.session_state.messages[-1]["content"]

    with st.chat_message("assistant"):
        with st.spinner("Evaluating multi-tier security boundaries..."):
            agent = Agent()

            # Automatically extract document path if specified
            doc_id = ""
            if "demo_pages/" in latest_prompt:
                for token in latest_prompt.split():
                    if token.startswith("demo_pages/"):
                        doc_id = token.strip(".,;:\"'")
                        break

            answer, trace = agent.run(latest_prompt, doc_id)

            # Analyze Interception Verdict
            alert_msg = None
            risk_badge = "0.0% Benign Safe"

            if "Tier 0 Kill Switch Triggered" in answer or "TIER0_CANARY_TRAP" in str(trace):
                alert_msg = "🚨 Threat Neutralized by Tier 0 Canary Trap! Data exfiltration aborted."
                risk_badge = "100% Intercepted (Canary)"
            elif "TIER1_FAST_GATEWAY" in str(trace) or "Hard trajectory killswitch" in answer:
                alert_msg = "🛑 Threat Intercepted by Tier 1 Fast Gateway! Unauthorized pivot killed."
                risk_badge = "100% Intercepted (Tier 1)"
            elif "Action blocked by AI Security Firewall" in answer:
                alert_msg = "⚠️ Action Blocked by Tier 2 Sentinel LLM!"
                risk_badge = "100% Intercepted (Tier 2)"

            if alert_msg:
                st.error(alert_msg)
            st.markdown(answer)

            if trace:
                with st.expander("🛡️ Firewall Inspection Trace"):
                    for step in trace:
                        st.markdown(f"**Step {step.get('step')} — Tool:** `{step.get('tool') or 'FINAL_ANSWER'}`")
                        if step.get("reasoning"):
                            st.caption(f"Reasoning: {step.get('reasoning')}")
                        st.json(step.get("input") or {})
                        st.code(step.get("output") or "No output")

            # Persist assistant turn
            st.session_state.messages.append({
                "role": "assistant",
                "content": answer,
                "alert": alert_msg,
                "trace": trace,
            })

            # Update sidebar chat history
            st.session_state.chats.insert(0, {
                "title": latest_prompt,
                "risk": risk_badge,
            })
            st.session_state.chats = st.session_state.chats[:6]

            st.rerun()