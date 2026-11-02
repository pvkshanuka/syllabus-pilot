"""Adaptive Study Recovery UI: Replanning missed sessions with Before & After Comparison."""
from datetime import date, datetime
import pandas as pd
import streamlit as st
from repositories.course_repository import CourseRepository
from repositories.study_repository import StudyRepository
from services.replanning import AdaptiveRecoveryEngine
from models.schemas import ReplanProposal


def render_recovery_page(course_repo: CourseRepository, study_repo: StudyRepository):
    """Renders the Adaptive Study Recovery Agent with Before-and-After review."""
    st.markdown("## 🔄 Adaptive Study Recovery Agent")
    st.markdown(
        "Life happens — illness, emergencies, or busy weeks can disrupt your study routine. "
        "The **Recovery Agent** recalculates your schedule, redistributes unfinished sessions into upcoming slots, "
        "and **strictly preserves** all your previously completed work."
    )

    courses = course_repo.list_courses()
    if not courses:
        st.warning("Please upload a syllabus first.")
        return

    course_options = {f"{c.course_name} ({c.course_code or 'No Code'})": c.id for c in courses}
    selected_lbl = st.selectbox("Select Course for Recovery:", list(course_options.keys()))
    course_id = course_options[selected_lbl]

    plan = study_repo.get_active_plan_for_course(course_id)
    if not plan or not plan.sessions:
        st.info("No study plan exists for this course yet. Generate one in the **Study Planner** first.")
        return

    assessments = course_repo.get_assessments(course_id)
    today = date.today()

    # 1. Detect missed sessions
    auto_missed = [s for s in plan.sessions if not s.is_completed and s.session_date < today.isoformat()]
    completed_sessions = [s for s in plan.sessions if s.is_completed]
    future_sessions = [s for s in plan.sessions if not s.is_completed and s.session_date >= today.isoformat()]

    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Completed Sessions (Preserved)", len(completed_sessions))
    with col_stat2:
        st.metric("Auto-Detected Overdue Sessions", len(auto_missed))
    with col_stat3:
        st.metric("Remaining Future Sessions", len(future_sessions))

    st.write("---")
    st.markdown("### 🛠️ Trigger Adaptive Replanning")

    with st.form("recovery_form"):
        reason = st.text_input(
            "Reason for schedule adjustment:",
            value="Illness / unexpected event caused missed study blocks.",
            help="Your reason will be recorded in the replan history log.",
        )

        # Simulation tool for testing / hackathon demonstration
        with st.expander("🧪 Demo Simulation: Select specific dates to mark as missed", expanded=False):
            session_dates = sorted(list({s.session_date for s in plan.sessions if not s.is_completed}))
            selected_missed_dates = st.multiselect(
                "Select dates you missed or will miss:",
                options=session_dates,
                default=[s.session_date for s in auto_missed[:3]],
            )

        submit_recovery = st.form_submit_button("🔍 Calculate Recovery Plan & Compare", type="primary", use_container_width=True)

    if submit_recovery:
        engine = AdaptiveRecoveryEngine()
        with st.spinner("Analyzing deadlines, calculating available slots, and shifting workload..."):
            proposal = engine.propose_recovery(
                current_plan=plan,
                current_date=today,
                missed_dates=selected_missed_dates,
                reason=reason,
                assessments=assessments,
            )
            st.session_state["active_recovery_proposal"] = proposal
            st.session_state["recovery_reason"] = reason

    # Display Before-and-After Review
    proposal: ReplanProposal = st.session_state.get("active_recovery_proposal")
    if proposal:
        st.write("---")
        st.markdown("### 📊 Before vs. After Schedule Comparison")

        st.info(f"💡 **Recovery Agent Assessment:** {proposal.explanation}")

        if proposal.warnings:
            for w in proposal.warnings:
                st.warning(f"⚠️ {w}")

        m_b1, m_b2, m_b3 = st.columns(3)
        with m_b1:
            st.metric("Missed Sessions Redistributed", len(proposal.missed_sessions))
        with m_b2:
            st.metric("Completed Work Intact", len(proposal.completed_sessions))
        with m_b3:
            st.metric("Net Total Hours Difference", f"{proposal.net_hours_difference:+.1f}h")

        # Visual Side-by-Side Comparison
        c_before, c_after = st.columns(2)
        with c_before:
            st.markdown("#### ⏳ Current Schedule")
            old_rows = []
            for s in plan.sessions:
                status_icon = "✅ Done" if s.is_completed else "❌ Missed" if s.session_date < today.isoformat() else "⏳ Future"
                old_rows.append({
                    "Date": s.session_date,
                    "Topic": s.topic,
                    "Assessment": s.assessment_name,
                    "Status": status_icon,
                })
            st.dataframe(pd.DataFrame(old_rows), use_container_width=True, height=300)

        with c_after:
            st.markdown("#### 🚀 Proposed Recovered Schedule")
            new_rows = []
            for s in proposal.redistributed_sessions:
                status_icon = "✅ Kept" if s.is_completed else "🔄 Rescheduled"
                new_rows.append({
                    "New Date": s.session_date,
                    "Topic": s.topic,
                    "Assessment": s.assessment_name,
                    "Status": status_icon,
                })
            st.dataframe(pd.DataFrame(new_rows), use_container_width=True, height=300)

        # Explicit Confirmation Step
        st.warning("⚠️ Changes will not take effect until you click confirm below.")
        col_apply, col_cancel = st.columns([2, 1])
        with col_apply:
            if st.button("✅ Confirm & Apply Recovered Schedule", type="primary", use_container_width=True):
                study_repo.replace_sessions(plan.id, proposal.redistributed_sessions)
                saved_reason = st.session_state.get("recovery_reason", "Adaptive Recovery")
                study_repo.record_replan_history(
                    plan_id=plan.id,
                    reason=saved_reason,
                    missed_count=len(proposal.missed_sessions),
                    redistributed_count=len(proposal.redistributed_sessions),
                    explanation=proposal.explanation,
                )
                del st.session_state["active_recovery_proposal"]
                st.success("🎉 Schedule successfully updated! All missed sessions have been recovered.")
                st.rerun()

        with col_cancel:
            if st.button("Discard Changes", use_container_width=True):
                del st.session_state["active_recovery_proposal"]
                st.info("Replan proposal discarded. Your current schedule was kept unchanged.")
                st.rerun()
