"""Study Planning Wizard, Weekly Schedule View, and Calendar Export."""
from datetime import date, datetime
import pandas as pd
import streamlit as st
from repositories.course_repository import CourseRepository
from repositories.study_repository import StudyRepository
from services.scheduling import StudyScheduler
from services.calendar_export import CalendarExporter
from models.schemas import StudyPreferences


def render_planner_page(course_repo: CourseRepository, study_repo: StudyRepository):
    """Renders the 3-question personalization wizard and generated schedule."""
    st.markdown("## 📅 Study Planner & Google Calendar Export")
    st.markdown(
        "Generate a conflict-free, week-by-week study schedule tailored to your weekly availability."
    )

    courses = course_repo.list_courses()
    if not courses:
        st.warning("No courses available. Please upload a syllabus first in the **Upload Syllabus** tab.")
        return

    # Select Course
    course_options = {f"{c.course_name} ({c.course_code or 'No Code'})": c.id for c in courses}
    default_idx = 0
    if "active_course_id" in st.session_state:
        for idx, (lbl, cid) in enumerate(course_options.items()):
            if cid == st.session_state["active_course_id"]:
                default_idx = idx
                break

    selected_course_lbl = st.selectbox("Select Course to Plan:", list(course_options.keys()), index=default_idx)
    course_id = course_options[selected_course_lbl]
    course = course_repo.get_course(course_id)
    assessments = course_repo.get_assessments(course_id)

    if not assessments:
        st.error("This course has no assessments listed. Please edit or add assessments in the Upload tab.")
        return

    existing_plan = study_repo.get_active_plan_for_course(course_id)

    # 3-Question Personalization Wizard
    st.markdown("### 🧙‍♂️ Personalization Wizard (Max 3 Questions)")
    with st.form("personalization_wizard_form"):
        col_q1, col_q2, col_q3 = st.columns(3)
        with col_q1:
            st.markdown("**1. Weekly Study Availability**")
            hours_per_week = st.slider(
                "Study hours per week:",
                min_value=2.0,
                max_value=35.0,
                value=float(existing_plan.preferences.hours_per_week if existing_plan else 10.0),
                step=1.0,
                help="Recommended effort is based on syllabus credits and assessment difficulty.",
            )
        with col_q2:
            st.markdown("**2. Available Days**")
            all_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            default_days = existing_plan.preferences.available_days if existing_plan else ["Monday", "Wednesday", "Friday", "Sunday"]
            available_days = st.multiselect(
                "Select available study days:",
                options=all_days,
                default=[d for d in default_days if d in all_days],
                help="Sessions will only be scheduled on these selected days.",
            )
        with col_q3:
            st.markdown("**3. Preferred Study Time**")
            time_choices = ["Morning (09:00 - 10:30)", "Afternoon (14:00 - 15:30)", "Evening (18:30 - 20:00)", "Night (20:30 - 22:00)"]
            default_time_idx = 2  # Evening
            if existing_plan:
                for idx, tc in enumerate(time_choices):
                    if existing_plan.preferences.preferred_time_of_day in tc:
                        default_time_idx = idx
            preferred_time_choice = st.selectbox("Preferred time block:", time_choices, index=default_time_idx)
            preferred_time_key = preferred_time_choice.split(" ")[0]

        # Optional Date Anchor
        with st.expander("⚙️ Optional: Advanced Date Alignment", expanded=False):
            start_date_val = st.text_input(
                "Schedule Start Date (YYYY-MM-DD):",
                value=course.semester_start or date.today().isoformat(),
                help="Defaults to semester start or today.",
            )

        generate_submitted = st.form_submit_button("🚀 Generate Autonomous Study Schedule", type="primary", use_container_width=True)

    if generate_submitted:
        if not available_days:
            st.error("Please select at least one available study day.")
            return

        scheduler = StudyScheduler()
        prefs = StudyPreferences(
            hours_per_week=hours_per_week,
            available_days=available_days,
            preferred_time_of_day=preferred_time_key,
            session_duration_hours=1.5,
            start_date=start_date_val,
        )

        with st.spinner("Generating deterministic schedule respecting deadlines and constraints..."):
            plan = scheduler.generate_plan(
                course_id=course_id,
                course_name=course.course_name,
                assessments=assessments,
                preferences=prefs,
            )
            plan_id = study_repo.save_plan(plan)
            st.session_state["active_plan_id"] = plan_id
            st.success(f"✨ Study Plan generated with {len(plan.sessions)} sessions totaling {plan.total_planned_hours} hours!")
            st.rerun()

    # Active Plan Display & Calendar View
    plan = study_repo.get_active_plan_for_course(course_id)
    if not plan or not plan.sessions:
        st.info("No active study plan generated yet. Fill the 3 questions above to build your schedule!")
        return

    st.write("---")
    st.markdown("### 🗓️ Generated Study Schedule & Google Calendar Export")
    
    # Plan Summary Stats & Calendar Download
    sum_col, dl_col = st.columns([2, 1])
    with sum_col:
        st.markdown(f"**Plan Summary:** {plan.summary}")
        if plan.warnings:
            for w in plan.warnings:
                st.caption(f"⚠️ {w}")
    with dl_col:
        exporter = CalendarExporter(default_timezone=plan.preferences.timezone)
        ics_bytes = exporter.export_plan_to_ics(plan, assessments=assessments)
        
        file_name = f"{course.course_name.replace(' ', '_')}_study_schedule.ics"
        st.download_button(
            label="📥 Download .ICS (Google Calendar)",
            data=ics_bytes,
            file_name=file_name,
            mime="text/calendar",
            type="primary",
            use_container_width=True,
        )

    # Google Calendar Import Instructions
    with st.expander("ℹ️ How to Import into Google Calendar", expanded=False):
        st.markdown("""
        **Quick 3-Step Google Calendar Import:**
        1. Click the **Download .ICS** button above to save the calendar file.
        2. Open [Google Calendar](https://calendar.google.com) on your browser.
        3. Click the **Gear icon (Settings) ⚙️ > Settings > Import & Export > Select file from your computer**, choose the downloaded file, and click **Import**!
        
        All your study blocks and assessment deadlines will populate into your Google Calendar instantly with notifications!
        """)

    # Interactive Schedule Table with completion toggles
    st.markdown("#### 📖 Study Sessions Breakdown")
    
    # Filter options
    filter_col1, filter_col2 = st.columns(2)
    with filter_col1:
        assessment_filter = st.selectbox(
            "Filter by Assessment:",
            ["All Assessments"] + sorted(list({s.assessment_name for s in plan.sessions})),
        )
    with filter_col2:
        status_filter = st.selectbox("Filter by Status:", ["All Sessions", "Pending Only", "Completed Only"])

    filtered_sessions = plan.sessions
    if assessment_filter != "All Assessments":
        filtered_sessions = [s for s in filtered_sessions if s.assessment_name == assessment_filter]
    if status_filter == "Pending Only":
        filtered_sessions = [s for s in filtered_sessions if not s.is_completed]
    elif status_filter == "Completed Only":
        filtered_sessions = [s for s in filtered_sessions if s.is_completed]

    # Display sessions as clean cards
    for s in filtered_sessions:
        badge = "badge-verified" if s.is_completed else "badge-low"
        status_text = "COMPLETED" if s.is_completed else "SCHEDULED"
        rev_tag = " &bull; <em>Final Revision</em>" if s.is_revision else ""
        
        col_s_info, col_s_check = st.columns([5, 1])
        with col_s_info:
            st.markdown(f"""
            <div class="sp-card" style="margin-bottom: 0.6rem; padding: 0.8rem 1.2rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <div>
                        <strong style="color: #0f172a; font-size: 1rem;">{s.topic}</strong>{rev_tag}
                        <div style="font-size: 0.85rem; color: #475569; margin-top: 0.2rem;">
                            📅 <strong>{s.session_date}</strong> &bull; ⏰ {s.start_time} - {s.end_time} ({s.duration_hours}h) &bull; 🎯 {s.assessment_name}
                        </div>
                    </div>
                    <span class="sp-badge {badge}">{status_text}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with col_s_check:
            st.write("")
            is_done = st.checkbox("Done", value=s.is_completed, key=f"sess_chk_{s.id}")
            if is_done != s.is_completed:
                study_repo.update_session_completion(s.id, is_done)
                st.rerun()
