"""Settings & Configuration Page for SyllabusPilot with Multi-Provider Support (Gemini & ChatGPT)."""
import os
import streamlit as st
from repositories.course_repository import CourseRepository
from repositories.study_repository import StudyRepository


def render_settings_page(course_repo: CourseRepository, study_repo: StudyRepository):
    """Renders environment settings, API key configuration, and database management."""
    st.markdown("## ⚙️ Application Settings & Configuration")

    st.markdown("### 🤖 AI Provider & Model Configuration")

    current_provider = os.getenv("AI_PROVIDER", "gemini").lower()
    provider_labels = {
        "gemini": "🔷 Google Gemini (Recommended for GDG Riga Hackathon)",
        "openai": "🟢 OpenAI (ChatGPT)",
    }
    provider_keys = list(provider_labels.keys())
    default_prov_idx = provider_keys.index(current_provider) if current_provider in provider_keys else 0

    selected_provider_label = st.radio(
        "Select Active AI Provider:",
        options=list(provider_labels.values()),
        index=default_prov_idx,
    )
    selected_provider = "gemini" if "Google Gemini" in selected_provider_label else "openai"

    st.write("")

    with st.form("api_key_form"):
        if selected_provider == "gemini":
            current_key = os.getenv("GEMINI_API_KEY", "")
            masked_key = f"{current_key[:6]}...{current_key[-4:]}" if len(current_key) > 10 else "Not Configured"
            st.caption(f"Gemini Status: **{'Configured (' + masked_key + ')' if current_key else 'Missing'}**")
            
            gemini_key = st.text_input(
                "Google Gemini API Key:",
                type="password",
                value=current_key,
                help="Get your free key at https://aistudio.google.com",
            )
            openai_key = os.getenv("OPENAI_API_KEY", "")

            available_models = ["gemini-2.5-pro", "gemini-3.8-pro", "gemini-1.5-pro", "gemini-3.8-flash"]
            current_model = os.getenv("GEMINI_MODEL", "gemini-2.5-pro")
            current_idx = available_models.index(current_model) if current_model in available_models else 0
            
            model_choice = st.selectbox(
                "Select Gemini Model (Pro & Flash):",
                available_models,
                index=current_idx,
                help="gemini-2.5-pro is Google's flagship Pro tier model with dedicated capacity and advanced extraction.",
            )
        else:
            current_key = os.getenv("OPENAI_API_KEY", "")
            masked_key = f"{current_key[:6]}...{current_key[-4:]}" if len(current_key) > 10 else "Not Configured"
            st.caption(f"OpenAI Status: **{'Configured (' + masked_key + ')' if current_key else 'Missing'}**")

            gemini_key = os.getenv("GEMINI_API_KEY", "")
            openai_key = st.text_input(
                "OpenAI API Key:",
                type="password",
                value=current_key,
                help="Get your key from https://platform.openai.com/api-keys",
            )

            available_models = ["gpt-4o-mini", "gpt-4o"]
            current_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            current_idx = available_models.index(current_model) if current_model in available_models else 0

            model_choice = st.selectbox(
                "Select ChatGPT Model:",
                available_models,
                index=current_idx,
                help="gpt-4o-mini provides fast and economical performance.",
            )

        save_api_btn = st.form_submit_button("Save AI Configuration", type="primary")

    if save_api_btn:
        os.environ["AI_PROVIDER"] = selected_provider
        if selected_provider == "gemini":
            os.environ["GEMINI_API_KEY"] = gemini_key.strip()
            os.environ["GEMINI_MODEL"] = model_choice
        else:
            os.environ["OPENAI_API_KEY"] = openai_key.strip()
            os.environ["OPENAI_MODEL"] = model_choice
        
        # Persist to .env file
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
        try:
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(f"AI_PROVIDER={selected_provider}\n")
                f.write(f"GEMINI_API_KEY={os.getenv('GEMINI_API_KEY', '')}\n")
                f.write(f"GEMINI_MODEL={os.getenv('GEMINI_MODEL', 'gemini-3.8-flash')}\n")
                f.write(f"OPENAI_API_KEY={os.getenv('OPENAI_API_KEY', '')}\n")
                f.write(f"OPENAI_MODEL={os.getenv('OPENAI_MODEL', 'gpt-4o-mini')}\n")
                f.write(f"DEFAULT_TIMEZONE={os.getenv('DEFAULT_TIMEZONE', 'Europe/Riga')}\n")
        except Exception:
            pass

        st.success(f"Config saved! Provider: **{selected_provider.upper()}** | Active Model: **{model_choice}**")
        st.rerun()

    st.write("---")
    st.markdown("### 🌍 Timezone & Calendar Settings")
    timezones = [
        "Europe/Riga",
        "Europe/London",
        "Europe/Berlin",
        "Europe/Helsinki",
        "America/New_York",
        "America/Los_Angeles",
        "Asia/Tokyo",
        "UTC",
    ]
    current_tz = os.getenv("DEFAULT_TIMEZONE", "Europe/Riga")
    selected_tz = st.selectbox("Application Timezone:", timezones, index=timezones.index(current_tz) if current_tz in timezones else 0)
    if st.button("Update Timezone"):
        os.environ["DEFAULT_TIMEZONE"] = selected_tz
        st.success(f"Timezone updated to {selected_tz}!")

    st.write("---")
    st.markdown("### 🗄️ Database Management")
    courses = course_repo.list_courses()
    st.markdown(f"Total Saved Courses: **{len(courses)}**")

    if courses:
        for c in courses:
            col_c_info, col_c_del = st.columns([4, 1])
            with col_c_info:
                st.write(f"📖 **{c.course_name}** (`{c.course_code or 'No Code'}`) - ID: {c.id}")
            with col_c_del:
                if st.button(f"🗑️ Delete", key=f"del_course_{c.id}"):
                    course_repo.delete_course(c.id)
                    st.success(f"Deleted course {c.course_name}.")
                    st.rerun()

    st.write("---")
    st.markdown("### 🧪 System Diagnostics & GDG Riga Hackathon Info")
    active_prov = os.getenv("AI_PROVIDER", "gemini").upper()
    active_mod = os.getenv("OPENAI_MODEL", "gpt-4o-mini") if active_prov == "OPENAI" else os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    st.code(
        f"Active AI Provider: {active_prov}\n"
        f"Active AI Model: {active_mod}\n"
        f"Database Path: {course_repo.db_path or 'syllabus_pilot.db'}\n"
        f"Google Gen AI SDK: google-genai 2.34.0\n"
        f"OpenAI SDK: openai 3.42.1\n"
        f"Frontend: Streamlit 1.66.1\n"
        f"Calendar Engine: icalendar 7.3.0\n"
        f"Validation: Pydantic 2.14.2",
        language="yaml",
    )
