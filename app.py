"""Main Streamlit Application Entrypoint for SyllabusPilot."""
import os
import streamlit as st
from dotenv import load_dotenv

from models.database import init_db
from repositories.course_repository import CourseRepository
from repositories.study_repository import StudyRepository
from ui.styles import apply_custom_styles
from ui.dashboard import render_dashboard
from ui.upload import render_upload_page
from ui.planner import render_planner_page
from ui.recovery import render_recovery_page
from ui.coach import render_coach_page
from ui.settings import render_settings_page

# Load environment configuration
load_dotenv()

# Streamlit Page Config
st.set_page_config(
    page_title="SyllabusPilot — AI Study Planning Agent",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Apply Modern SaaS Styling
apply_custom_styles()

# Initialize Local Database
init_db()
course_repo = CourseRepository()
study_repo = StudyRepository()


def main():
    # Sidebar Navigation & Branding
    with st.sidebar:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 1.5rem;">
            <span style="font-size: 2.2rem;">🎓</span>
            <div>
                <h2 style="margin: 0; font-size: 1.35rem; color: #0f172a; font-weight: 700;">SyllabusPilot</h2>
                <span style="font-size: 0.75rem; color: #0d9488; font-weight: 600; text-transform: uppercase;">GDG Riga AI Hackathon</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

        pages = [
            "📊 Dashboard Overview",
            "📄 Upload & Extract Syllabus",
            "📅 Study Planner & ICS",
            "🔄 Adaptive Study Recovery",
            "💡 AI Study Coach & Quizzes",
            "⚙️ Settings",
        ]
        
        selected_page = st.radio("Navigation", pages, label_visibility="collapsed")

        st.markdown("---")
        
        # Sidebar Quick Status
        courses = course_repo.list_courses()
        st.markdown(f"📚 **Enrolled Courses:** {len(courses)}")
        if courses:
            total_active_hours = 0.0
            for c in courses:
                p = study_repo.get_active_plan_for_course(c.id)
                if p:
                    total_active_hours += p.total_planned_hours
            st.markdown(f"⏱️ **Planned Study Hours:** {total_active_hours:.1f}h")

        st.markdown("---")
        st.caption("🚀 Built for GDG Riga AI Agents Hackathon\nPowered by Google Gemini & ADK")

    # Routing
    if selected_page == "📊 Dashboard Overview":
        render_dashboard(course_repo, study_repo)
    elif selected_page == "📄 Upload & Extract Syllabus":
        render_upload_page(course_repo)
    elif selected_page == "📅 Study Planner & ICS":
        render_planner_page(course_repo, study_repo)
    elif selected_page == "🔄 Adaptive Study Recovery":
        render_recovery_page(course_repo, study_repo)
    elif selected_page == "💡 AI Study Coach & Quizzes":
        render_coach_page(course_repo, study_repo)
    elif selected_page == "⚙️ Settings":
        render_settings_page(course_repo, study_repo)


if __name__ == "__main__":
    main()
