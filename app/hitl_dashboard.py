"""HITL monitoring dashboard and analytics"""
import streamlit as st
from tools.hitl_audit import get_audit_log
from datetime import datetime, timedelta


def render_hitl_dashboard():
    """Render HITL analytics dashboard in sidebar"""
    st.sidebar.markdown("### 📊 HITL Analytics")

    audit_log = get_audit_log()
    summary = audit_log.get_session_summary()
    rates = audit_log.get_gate_decision_rate()

    # Summary metrics
    col1, col2 = st.sidebar.columns(2)
    with col1:
        st.metric("Gates Triggered", summary["gates_triggered"])
    with col2:
        st.metric("Decisions Made", summary["decisions_made"])

    # Approval rates
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        st.metric("✓ Approved", summary["approved"])
    with col2:
        st.metric("✗ Denied", summary["denied"])
    with col3:
        total = summary["approved"] + summary["denied"]
        rate = (summary["approved"] / total * 100) if total > 0 else 0
        st.metric("Approval %", f"{rate:.0f}%")

    # Auto-decisions
    if summary["auto_approved"] > 0 or summary["auto_denied"] > 0:
        st.sidebar.markdown("**Auto-Decisions:**")
        col1, col2 = st.sidebar.columns(2)
        with col1:
            st.caption(f"✓ Auto-Approved: {summary['auto_approved']}")
        with col2:
            st.caption(f"✗ Auto-Denied: {summary['auto_denied']}")

    # Breakdown by gate type
    if summary["triggers_by_reason"]:
        with st.sidebar.expander("📈 By Gate Type", expanded=False):
            for reason, count in sorted(
                summary["triggers_by_reason"].items(), key=lambda x: -x[1]
            ):
                gate_rates = rates.get(reason, {})
                approval_rate = gate_rates.get("approval_rate", 0)
                total = gate_rates.get("total", 0)

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.caption(f"{reason.replace('_', ' ').title()}")
                with col2:
                    st.caption(f"{count} triggered")
                with col3:
                    if total > 0:
                        st.caption(f"{approval_rate*100:.0f}% approved")


def render_hitl_statistics():
    """Render detailed HITL statistics page"""
    st.header("📊 HITL Statistics Dashboard")

    audit_log = get_audit_log()
    summary = audit_log.get_session_summary()
    rates = audit_log.get_gate_decision_rate()

    # Summary cards
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Gates Triggered",
            summary["gates_triggered"],
            help="Total number of HITL gates triggered today",
        )

    with col2:
        st.metric(
            "Total Decisions",
            summary["decisions_made"],
            help="Total decisions made by human reviewers",
        )

    with col3:
        total = summary["approved"] + summary["denied"]
        rate = (summary["approved"] / total * 100) if total > 0 else 0
        st.metric(
            "Approval Rate",
            f"{rate:.1f}%",
            help="Percentage of approved vs. denied decisions",
        )

    with col4:
        auto_total = summary["auto_approved"] + summary["auto_denied"]
        st.metric(
            "Auto-Decisions",
            auto_total,
            help="Decisions made automatically by the system",
        )

    st.divider()

    # Breakdown by gate type
    if rates:
        st.subheader("🚪 Decision Breakdown by Gate Type")

        col1, col2 = st.columns([2, 1])

        with col1:
            # Create a table
            gate_data = []
            for reason, stats in sorted(
                rates.items(), key=lambda x: -x[1]["total"]
            ):
                gate_data.append({
                    "Gate Type": reason.replace("_", " ").title(),
                    "Triggered": stats["total"],
                    "Approved": stats["approved"],
                    "Denied": stats["denied"],
                    "Approval %": f"{stats['approval_rate']*100:.1f}%",
                })

            st.dataframe(
                gate_data,
                use_container_width=True,
                hide_index=True,
            )

        with col2:
            # Gate trigger distribution (pie chart)
            labels = [
                r.replace("_", " ").title() for r in rates.keys()
            ]
            sizes = [rates[r]["total"] for r in rates.keys()]

            st.caption("**Gate Distribution**")
            if sizes:
                import plotly.graph_objects as go
                fig = go.Figure(data=[go.Pie(labels=labels, values=sizes)])
                st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # Auto-decision reasons
    if summary["auto_approved"] > 0 or summary["auto_denied"] > 0:
        st.subheader("⚙️ Auto-Approval Statistics")
        col1, col2 = st.columns(2)

        with col1:
            st.metric("Auto-Approved", summary["auto_approved"])
        with col2:
            st.metric("Auto-Denied", summary["auto_denied"])

    # Recommendations
    st.divider()
    st.subheader("💡 Insights & Recommendations")

    insights = []

    if summary["gates_triggered"] > 50:
        insights.append(
            "⚠️ High gate trigger rate - Consider adjusting confidence thresholds to reduce false positives"
        )

    if rates:
        avg_approval_rate = sum(r["approval_rate"] for r in rates.values()) / len(rates)
        if avg_approval_rate > 0.9:
            insights.append(
                "✓ High approval rate - Gates are well-calibrated for legitimate scenarios"
            )
        elif avg_approval_rate < 0.5:
            insights.append(
                "⚠️ Low approval rate - Consider reviewing gate trigger criteria"
            )

    if "low_confidence" in rates:
        conf_rate = rates["low_confidence"]["approval_rate"]
        if conf_rate > 0.7:
            insights.append(
                "ℹ️ Most low-confidence responses are being approved - verify they're still valid"
            )

    if insights:
        for insight in insights:
            st.info(insight)
    else:
        st.success("✓ All systems performing normally")


def render_recent_decisions(limit: int = 10):
    """Render recent HITL decisions"""
    st.subheader("📋 Recent Decisions")

    audit_log = get_audit_log()

    # This would read from the audit log file
    decisions = []
    try:
        import json
        if audit_log.session_log_file.exists():
            with open(audit_log.session_log_file, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("event_type") == "decision_made":
                        decisions.append(entry)

        if decisions:
            decisions = decisions[-limit:][::-1]  # Most recent first

            for decision in decisions:
                status = "✓ Approved" if decision.get("approved") else "✗ Denied"
                reason = decision.get("trigger_reason", "unknown").replace("_", " ").title()
                timestamp = decision.get("timestamp", "")

                with st.container(border=True):
                    col1, col2, col3 = st.columns([2, 1, 1])
                    with col1:
                        st.caption(f"**{reason}**")
                    with col2:
                        st.caption(status)
                    with col3:
                        st.caption(timestamp[-8:])  # Show time only

                    if decision.get("reviewer_note"):
                        st.caption(f"*Note: {decision['reviewer_note']}*")
        else:
            st.info("No decisions recorded yet")

    except Exception as e:
        st.error(f"Error loading decisions: {e}")
