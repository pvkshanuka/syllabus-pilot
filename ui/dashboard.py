"""Dashboard Overview UI for SyllabusPilot."""
from datetime import date, datetime
import streamlit as st
from repositories.course_repository import CourseRepository
from repositories.study_repository import StudyRepository
from services.priority import WorkloadBalancer
from services.study_coach import StudyCoachService


def render_dashboard(course_repo: CourseRepository, study_repo: StudyRepository):
    """Renders the comprehensive Dashboard Overview."""
    st.markdown("""
    <div class="sp-hero">
        <h1>Welcome to SyllabusPilot 🎓</h1>
        <p>AI-Powered Autonomous Study Planning Agent for Academic Excellence</p>
    </div>
    """, unsafe_allow_html=True)

    courses = course_repo.list_courses()
    if not courses:
        st.info("👋 Welcome! You haven't added any courses yet. Head to **Upload Syllabus** in the sidebar to get started with a PDF, photo, or pasted syllabus!")
        col1, col2 = st.columns([1, 3])
        with col1:
            if st.button("🚀 Load Sample Course (CS101)", type="primary"):
                from agent.tools import SyllabusPilotTools
                tools = SyllabusPilotTools(db_path=course_repo.db_path)
                with open("samples/sample_cs101_syllabus.txt", "r", encoding="utf-8") as f:
                    text = f.read()
                res = tools.extract_syllabus_information(text)
                tools.generate_study_plan(course_id=res["course_id"], hours_per_week=10.0, start_date="2026-11-03")
                st.success("Sample CS101 course and study plan loaded! Refreshing...")
                st.rerun()
        return

    # Select Active Course
    course_options = {f"{c.course_name} ({c.course_code or 'No Code'})": c.id for c in courses}
    selected_label = st.selectbox("📚 Select Active Course:", list(course_options.keys()))
    course_id = course_options[selected_label]
    
    course = course_repo.get_course(course_id)
    assessments = course_repo.get_assessments(course_id)
    plan = study_repo.get_active_plan_for_course(course_id)

    # Calculate Metrics
    today = date.today()
    upcoming_deadlines = [
        a for a in assessments if a.deadline and a.deadline[:10] >= today.isoformat()
    ]
    
    metrics = study_repo.get_progress_metrics(plan.id) if plan else {
        "total_sessions": 0, "total_hours": 0.0, "completed_sessions": 0,
        "completed_hours": 0.0, "remaining_hours": 0.0, "progress_percentage": 0.0,
    }

    # 1. Top Stat Cards
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1:
        st.markdown(f"""
        <div class="sp-metric-box">
            <div class="sp-metric-title">Total Courses</div>
            <div class="sp-metric-value">{len(courses)}</div>
            <div class="sp-metric-subtitle">Active Academic Term</div>
        </div>
        """, unsafe_allow_html=True)
    with m2:
        st.markdown(f"""
        <div class="sp-metric-box">
            <div class="sp-metric-title">Upcoming Deadlines</div>
            <div class="sp-metric-value">{len(upcoming_deadlines)}</div>
            <div class="sp-metric-subtitle">Next: {upcoming_deadlines[0].deadline[:10] if upcoming_deadlines else 'None'}</div>
        </div>
        """, unsafe_allow_html=True)
    with m3:
        st.markdown(f"""
        <div class="sp-metric-box">
            <div class="sp-metric-title">Planned Hours</div>
            <div class="sp-metric-value">{metrics['total_hours']}h</div>
            <div class="sp-metric-subtitle">{metrics['total_sessions']} Total Sessions</div>
        </div>
        """, unsafe_allow_html=True)
    with m4:
        st.markdown(f"""
        <div class="sp-metric-box">
            <div class="sp-metric-title">Completed Hours</div>
            <div class="sp-metric-value">{metrics['completed_hours']}h</div>
            <div class="sp-metric-subtitle">{metrics['completed_sessions']} Completed</div>
        </div>
        """, unsafe_allow_html=True)
    with m5:
        st.markdown(f"""
        <div class="sp-metric-box">
            <div class="sp-metric-title">Overall Progress</div>
            <div class="sp-metric-value">{metrics['progress_percentage']}%</div>
            <div class="sp-metric-subtitle">{metrics['remaining_hours']}h Remaining</div>
        </div>
        """, unsafe_allow_html=True)

    st.write("")

    # 2. Next Recommended Study Session Hero Card
    coach = StudyCoachService()
    if plan and plan.sessions:
        next_session = coach.suggest_next_session(plan, reference_date=today)
        if next_session:
            st.markdown("### ⚡ Next Recommended Study Session")
            with st.container():
                tip = coach.generate_revision_recommendation(
                    course_name=next_session.course_name,
                    topic=next_session.topic,
                    assessment_name=next_session.assessment_name,
                )
                col_info, col_action = st.columns([3, 1])
                with col_info:
                    st.markdown(f"""
                    <div class="sp-card" style="border-left: 5px solid #0d9488;">
                        <h4 style="margin: 0 0 0.5rem 0; color: #0f172a;">📖 {next_session.topic}</h4>
                        <p style="margin: 0 0 0.5rem 0; color: #475569;">
                            <strong>Course:</strong> {next_session.course_name} &nbsp;|&nbsp; 
                            <strong>Target Assessment:</strong> {next_session.assessment_name} &nbsp;|&nbsp; 
                            <strong>Scheduled:</strong> {next_session.session_date} ({next_session.start_time} - {next_session.end_time})
                        </p>
                        <p style="margin: 0; font-size: 0.9rem; color: #0f766e; background: #f0fdfa; padding: 0.5rem 0.75rem; border-radius: 6px;">
                            <strong>Study Coach Strategy:</strong> {tip}
                        </p>
                    </div>
                    """, unsafe_allow_html=True)
                with col_action:
                    st.write("")
                    st.write("")
                    if st.button("✅ Mark Session Complete", key=f"dash_done_{next_session.id}", type="primary"):
                        study_repo.update_session_completion(next_session.id, True, "Completed via Dashboard")
                        st.toast("Great job completing your study block! 🎉")
                        st.rerun()

    # 3. Two Columns: High Priority Deadlines & Upcoming Sessions
    c_left, c_right = st.columns(2)

    with c_left:
        st.markdown("### 🎯 Critical Assessment Priorities")
        balancer = WorkloadBalancer()
        priorities = balancer.calculate_priorities(assessments, plan.sessions if plan else [])
        if priorities:
            for p in priorities[:4]:
                badge_class = "badge-high" if p.priority_tier == "High" else "badge-medium" if p.priority_tier == "Medium" else "badge-low"
                st.markdown(f"""
                <div class="sp-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                        <strong style="font-size: 1.05rem; color: #1e293b;">{p.assessment_name}</strong>
                        <span class="sp-badge {badge_class}">{p.priority_tier} ({p.priority_score:.0f}/100)</span>
                    </div>
                    <p style="margin: 0; color: #64748b; font-size: 0.85rem;">
                        📅 Deadline: <strong>{p.deadline or 'TBA'}</strong> &nbsp;|&nbsp; 
                        ⚖️ Weight: <strong>{p.weight_percentage}%</strong> &nbsp;|&nbsp; 
                        ⏱️ Est. Effort: <strong>{p.estimated_effort_hours}h</strong>
                    </p>
                    <p style="margin: 0.4rem 0 0 0; color: #334155; font-size: 0.85rem;">{p.explanation}</p>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No assessments found for this course.")

    with c_right:
        st.markdown("### 📅 Upcoming Scheduled Sessions")
        if plan and plan.sessions:
            uncompleted_sessions = [s for s in plan.sessions if not s.is_completed][:5]
            if uncompleted_sessions:
                for s in uncompleted_sessions:
                    is_rev = " [Revision]" if s.is_revision else ""
                    st.markdown(f"""
                    <div class="sp-card" style="padding: 0.9rem 1.2rem;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <div>
                                <strong style="color: #0f172a;">{s.topic}{is_rev}</strong>
                                <div style="font-size: 0.8rem; color: #64748b; margin-top: 0.2rem;">
                                    {s.session_date} &bull; {s.start_time}-{s.end_time} &bull; {s.assessment_name}
                                </div>
                            </div>
                            <span class="sp-badge badge-low">{s.duration_hours}h</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.success("All planned sessions are complete! You are fully prepped! 🎉")
        else:
            st.info("No study plan generated yet for this course. Visit the **Study Planner** tab to generate your schedule!")
