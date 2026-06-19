"""Reusable Streamlit UI components"""
import streamlit as st
from datetime import datetime


def render_response_card(response, sources=None, confidence=0.0):
    """Render a formatted response card"""
    col1, col2 = st.columns([0.85, 0.15])

    with col1:
        st.markdown(response)

    with col2:
        confidence_pct = confidence * 100
        if confidence >= 0.75:
            st.markdown(f'<span class="success">✓ {confidence_pct:.0f}%</span>', unsafe_allow_html=True)
        elif confidence >= 0.5:
            st.markdown(f'<span class="warning">⚠ {confidence_pct:.0f}%</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="error">✗ {confidence_pct:.0f}%</span>', unsafe_allow_html=True)

    if sources:
        with st.expander("Sources", expanded=False):
            for source in sources:
                st.markdown(f"""
                **Collection**: {source.get('collection')}
                **ID**: `{source.get('chunk_id')}`
                **Freshness**: {source.get('metadata', {}).get('fetched_at', 'unknown')}
                """)


def render_hitl_gate(gate_info, trigger_id=None):
    """Render HITL gate approval panel"""
    st.markdown(f"""
    <div class="hitl-panel">
    <strong>🚨 {gate_info.get('gate', 'Unknown Gate')}</strong><br>
    {gate_info.get('reason', 'No details')}
    </div>
    """, unsafe_allow_html=True)

    details = gate_info.get('details', {})
    if details:
        with st.expander("Details"):
            for key, value in details.items():
                st.markdown(f"**{key}**: {value}")

    col1, col2, col3 = st.columns(3)
    with col1:
        approve = st.button("✓ Approve", key=f"approve_{trigger_id}")
    with col2:
        deny = st.button("✗ Deny", key=f"deny_{trigger_id}")
    with col3:
        request_info = st.button("❓ More Info", key=f"info_{trigger_id}")

    return approve, deny, request_info


def render_tool_call_trace(tool_name: str, args: dict, result: dict, latency_ms: float):
    """Render tool call execution trace"""
    st.markdown(f"""
    <div class="tool-call">
    <strong>{tool_name}</strong> ({latency_ms:.0f}ms)<br>
    <code>{str(args)[:100]}...</code>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.json({"args": args})
    with col2:
        st.json({"result": result})


def render_session_stats(turn_count: int, tool_count: int, hitl_count: int):
    """Render session statistics dashboard"""
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Turns", turn_count, delta=0)
    with col2:
        st.metric("Tool Calls", tool_count, delta=0)
    with col3:
        st.metric("HITL Gates", hitl_count, delta=0 if hitl_count == 0 else None)


def render_intent_badge(intent: str):
    """Render intent classification badge"""
    intent_colors = {
        "sql_only": "🔵",
        "rag_only": "🟡",
        "cross_domain": "🟢",
        "meta": "🟣",
        "unclear": "🔴",
        "error": "⚫",
    }
    icon = intent_colors.get(intent, "❓")
    st.markdown(f"{icon} **Intent**: {intent}")


def render_freshness_indicator(fetched_at: str, threshold_hours: int = 6):
    """Render data freshness indicator"""
    from datetime import datetime, timezone, timedelta

    try:
        fetch_time = datetime.fromisoformat(fetched_at.replace("Z", "+00:00"))
        age_hours = (datetime.now(timezone.utc) - fetch_time).total_seconds() / 3600

        if age_hours < threshold_hours:
            st.markdown(f'<span class="success">✓ Fresh ({age_hours:.0f}h old)</span>', unsafe_allow_html=True)
        else:
            st.markdown(f'<span class="warning">⚠ Stale ({age_hours:.0f}h old)</span>', unsafe_allow_html=True)
    except Exception as e:
        st.markdown(f'<span class="error">? Unknown</span>', unsafe_allow_html=True)


def render_error_message(error: str, severity: str = "error"):
    """Render error message with severity"""
    if severity == "error":
        st.error(error)
    elif severity == "warning":
        st.warning(error)
    else:
        st.info(error)


def render_loading_spinner(message: str = "Processing..."):
    """Render loading spinner with message"""
    with st.spinner(message):
        st.markdown(f"⏳ {message}")
