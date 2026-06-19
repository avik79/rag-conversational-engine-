"""Main Streamlit application entry point"""
import streamlit as st
import asyncio
import os
from datetime import datetime
import sys

sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables explicitly
from dotenv import load_dotenv
env_path = ".env"
if os.path.exists(env_path):
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Direct Anthropic integration - no tools wiring needed
from models.pydantic_io import EIRAResponse

# Configure Streamlit
st.set_page_config(
    page_title="RAG Conversational Engine",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
    <style>
    .main {
        padding-top: 2rem;
    }
    .stChatMessage {
        background-color: #f0f2f6;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
    .hitl-panel {
        background-color: #fff3cd;
        border: 2px solid #ffc107;
        border-radius: 0.5rem;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .tool-call {
        background-color: #e7f3ff;
        border-left: 4px solid #0066cc;
        padding: 0.75rem;
        margin: 0.5rem 0;
        border-radius: 0.25rem;
        font-family: monospace;
        font-size: 0.85rem;
    }
    .success {
        color: #28a745;
        font-weight: 600;
    }
    .warning {
        color: #ff9800;
        font-weight: 600;
    }
    .error {
        color: #dc3545;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize Streamlit session state"""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "hitl_queue" not in st.session_state:
        st.session_state.hitl_queue = []
    if "tool_traces" not in st.session_state:
        st.session_state.tool_traces = []
    if "turn_count" not in st.session_state:
        st.session_state.turn_count = 0
    if "user_name" not in st.session_state:
        st.session_state.user_name = "User"
    # Note: wire_all_tools() not needed - using direct Anthropic integration


async def run_agent_with_hooks(user_input: str):
    """Run EIRA agent with pre/post tool hooks (or demo mode if APIs unavailable)"""
    from app.integration import run_eira_agent
    from app.demo_mode import get_demo_response

    st.session_state.turn_count += 1

    try:
        context = await run_eira_agent(
            user_input,
            turn_count=st.session_state.turn_count,
            user_name=st.session_state.user_name,
        )

        # Track HITL gates
        if hasattr(context, 'hitl_decisions') and context.hitl_decisions:
            st.session_state.hitl_queue.extend(context.hitl_decisions)

        # Track tool calls
        if hasattr(context, 'tool_calls') and context.tool_calls:
            for call in context.tool_calls:
                st.session_state.tool_traces.append({
                    "tool": call.get("name"),
                    "args": call.get("args"),
                    "result": call.get("result"),
                    "latency_ms": call.get("latency_ms", 0),
                    "timestamp": datetime.utcnow().isoformat(),
                })

        return context.response
    except Exception as e:
        # Fall back to demo mode on API errors
        if "credentials" in str(e).lower() or "api_key" in str(e).lower():
            st.info("Using demo mode (real APIs not configured)")
            demo_response = get_demo_response(user_input)
            st.session_state.tool_traces.append({
                "tool": "demo_mode",
                "latency_ms": 0,
                "timestamp": datetime.utcnow().isoformat(),
            })
            return demo_response
        else:
            st.error(f"Agent error: {e}")
            return None


def render_chat_interface():
    """Render main chat interface"""
    st.title("🧠 RAG Conversational Engine")
    st.markdown("Query employee data, weather, and news with intelligent routing and human approval gates.")

    # Chat display
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.messages:
            with st.chat_message(message["role"], avatar="🧠" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])
                if "tool_calls" in message:
                    with st.expander("Tool calls", expanded=False):
                        for call in message["tool_calls"]:
                            st.markdown(f"""
                            <div class="tool-call">
                            <strong>{call['name']}</strong><br>
                            {call['status']}
                            </div>
                            """, unsafe_allow_html=True)

    # Chat input
    if user_input := st.chat_input("Ask me about employees, weather, or news..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🧠"):
            try:
                response = asyncio.run(run_agent_with_hooks(user_input))
                if response:
                    st.markdown(response.answer)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response.answer,
                        "confidence": response.confidence,
                    })
            except Exception as e:
                st.error(f"Error: {e}")


def render_hitl_panel():
    """Render HITL approval sidebar"""
    with st.sidebar:
        st.markdown("### 🚨 Human-in-the-Loop Gates")

        if not st.session_state.hitl_queue:
            st.info("No pending approvals")
            return

        for i, trigger in enumerate(st.session_state.hitl_queue):
            with st.container():
                st.markdown(f"""
                <div class="hitl-panel">
                <strong>Gate: {trigger['gate']}</strong><br>
                {trigger['reason']}
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Approve", key=f"approve_{i}"):
                        st.session_state.hitl_queue.pop(i)
                        st.success("Approved")
                        st.rerun()
                with col2:
                    if st.button("Deny", key=f"deny_{i}"):
                        st.session_state.hitl_queue.pop(i)
                        st.warning("Denied")
                        st.rerun()


def render_sidebar():
    """Render sidebar with settings and traces"""
    with st.sidebar:
        st.markdown("### ⚙️ Settings")

        st.session_state.user_name = st.text_input(
            "User Name",
            value=st.session_state.user_name,
        )

        st.markdown("### 📊 Session Info")
        st.metric("Turn Count", st.session_state.turn_count)
        st.metric("Tool Traces", len(st.session_state.tool_traces))

        if st.checkbox("Show tool traces"):
            st.markdown("#### Tool Execution Traces")
            for trace in st.session_state.tool_traces[-5:]:  # Last 5
                with st.expander(f"{trace['tool']} ({trace['latency_ms']:.0f}ms)"):
                    st.json(trace["result"])

        if st.button("Clear Session"):
            st.session_state.clear()
            st.rerun()


def main():
    """Main application flow"""
    init_session_state()
    render_sidebar()
    render_hitl_panel()
    render_chat_interface()


if __name__ == "__main__":
    main()
