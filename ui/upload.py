"""Upload & Extract Syllabus Page with Editable Data Table."""
import os
import pandas as pd
import streamlit as st
from services.extraction import SyllabusExtractor
from repositories.course_repository import CourseRepository
from models.schemas import AssessmentItem, CourseMetadata, AssessmentType, VerificationStatus


def render_upload_page(course_repo: CourseRepository):
    """Renders the syllabus upload, multimodal parsing, and interactive editor."""
    st.markdown("## 📄 Upload & Extract Course Syllabus")
    active_prov = os.getenv("AI_PROVIDER", "gemini").title()
    active_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini") if active_prov.lower() == "openai" else os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
    st.markdown(
        f"Upload a syllabus as a **PDF**, **photo (JPG/PNG)**, or **paste syllabus text**. "
        f"Multimodal AI analysis (**{active_prov}: `{active_model}`**) extracts course details, deadlines, weights, and topics."
    )

    extractor = SyllabusExtractor(model_name=active_model)

    # Pre-load sample buttons
    with st.expander("💡 Fast Demo: Load Sample Syllabi", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            if st.button("📥 Load CS101: Computer Science Syllabus"):
                with open("samples/sample_cs101_syllabus.txt", "r", encoding="utf-8") as f:
                    st.session_state["pasted_text_input"] = f.read()
                st.session_state["upload_tab_choice"] = "Paste Text"
                st.rerun()
        with c2:
            if st.button("📥 Load DS301: Data Science Syllabus"):
                with open("samples/sample_datascience_syllabus.txt", "r", encoding="utf-8") as f:
                    st.session_state["pasted_text_input"] = f.read()
                st.session_state["upload_tab_choice"] = "Paste Text"
                st.rerun()

    tab_upload, tab_paste = st.tabs(["📁 File Upload (PDF, JPG, PNG)", "✍️ Paste Text"])

    extracted_result = None

    with tab_upload:
        uploaded_file = st.file_uploader(
            "Choose a syllabus document or photo",
            type=["pdf", "png", "jpg", "jpeg"],
            help="Supported formats: PDF, PNG, JPG. Max size 25MB.",
        )
        if uploaded_file is not None:
            st.info(f"Selected: **{uploaded_file.name}** ({uploaded_file.size / 1024:.1f} KB)")
            if st.button("🔍 Extract Syllabus Data with Gemini", key="btn_extract_file", type="primary"):
                with st.spinner("Analyzing document with Gemini Multimodal AI..."):
                    try:
                        file_bytes = uploaded_file.read()
                        if uploaded_file.type == "application/pdf":
                            extracted_result = extractor.extract_from_pdf(file_bytes, file_name=uploaded_file.name)
                        elif uploaded_file.type in ("image/jpeg", "image/png", "image/jpg"):
                            extracted_result = extractor.extract_from_image(file_bytes, mime_type=uploaded_file.type)
                        else:
                            st.error("Unsupported file type.")
                        
                        st.session_state["latest_extracted"] = extracted_result
                        st.success("Syllabus successfully extracted!")
                    except Exception as e:
                        st.error(f"Extraction failed: {str(e)}")

    with tab_paste:
        default_paste = st.session_state.get("pasted_text_input", "")
        text_content = st.text_area(
            "Paste full or partial syllabus text here:",
            value=default_paste,
            height=250,
            placeholder="COURSE SYLLABUS\nCS101: Foundations of Computer Science\nFall 2026\n...",
        )
        if st.button("🔍 Analyze Pasted Syllabus", key="btn_extract_text", type="primary"):
            if not text_content.strip():
                st.warning("Please paste some syllabus text first.")
            else:
                with st.spinner("Extracting course entities and deadlines..."):
                    try:
                        extracted_result = extractor.extract_from_text(text_content)
                        st.session_state["latest_extracted"] = extracted_result
                        st.success("Syllabus text successfully analyzed!")
                    except Exception as e:
                        st.error(f"Extraction error: {str(e)}")

    # Display Extracted Data & Editable Review Table
    current_extracted = st.session_state.get("latest_extracted")
    if current_extracted:
        st.write("---")
        st.markdown("### 📋 Review & Edit Extracted Course Data")
        
        # Course Metadata Form
        with st.container():
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                c_name = st.text_input("Course Name:", value=current_extracted.course.course_name)
            with col_c2:
                c_code = st.text_input("Course Code:", value=current_extracted.course.course_code or "")
            with col_c3:
                c_instructor = st.text_input("Instructor:", value=current_extracted.course.instructor_name or "")

            col_d1, col_d2, col_d3 = st.columns(3)
            with col_d1:
                sem_start = st.text_input("Semester Start (YYYY-MM-DD):", value=current_extracted.course.semester_start or "")
            with col_d2:
                sem_end = st.text_input("Semester End (YYYY-MM-DD):", value=current_extracted.course.semester_end or "")
            with col_d3:
                rec_hours = st.number_input(
                    "Recommended Study Hours/Wk:",
                    value=float(current_extracted.course.study_hours_recommended_per_week or 8.0),
                    min_value=1.0,
                    max_value=40.0,
                    step=1.0,
                )

        if current_extracted.unparsed_notes:
            st.caption(f"ℹ️ **Extraction Note:** {current_extracted.unparsed_notes}")

        st.markdown("#### 📝 Extracted Assessment Schedule (Editable)")
        st.markdown(
            "Review extracted deadlines and percentages. You can edit table cells directly before saving."
        )

        # Build DataFrame for st.data_editor
        assessment_rows = []
        for a in current_extracted.assessments:
            assessment_rows.append({
                "Name": a.name,
                "Type": a.assessment_type.value if hasattr(a.assessment_type, 'value') else str(a.assessment_type),
                "Deadline": a.deadline or "",
                "Weight (%)": float(a.weight_percentage or 0.0),
                "Topics": ", ".join(a.topics),
                "Status": a.verification_status.value if hasattr(a.verification_status, 'value') else str(a.verification_status),
            })

        df_assessments = pd.DataFrame(assessment_rows)

        edited_df = st.data_editor(
            df_assessments,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "Name": st.column_config.TextColumn("Assessment Name", required=True),
                "Type": st.column_config.SelectboxColumn(
                    "Type",
                    options=["Exam", "Midterm", "Final", "Assignment", "Project", "Quiz", "Lab", "Presentation", "Other"],
                    required=True,
                ),
                "Deadline": st.column_config.TextColumn("Deadline (YYYY-MM-DD)", required=False),
                "Weight (%)": st.column_config.NumberColumn("Weight (%)", min_value=0.0, max_value=100.0, step=1.0),
                "Topics": st.column_config.TextColumn("Covered Topics"),
                "Status": st.column_config.SelectboxColumn("Verification Status", options=["Verified", "Needs Review", "Confirmed by User"]),
            },
            key="assessments_editor",
        )

        total_weight = edited_df["Weight (%)"].sum() if not edited_df.empty else 0.0
        if abs(total_weight - 100.0) > 1.0:
            st.warning(f"⚠️ Total grading weight is currently **{total_weight:.1f}%** (Expected ~100%).")
        else:
            st.success(f"✅ Total grading weight is balanced: **{total_weight:.1f}%**.")

        # Save to Database Button
        if st.button("💾 Confirm & Save Course to Database", type="primary", use_container_width=True):
            # Reconstruct Pydantic items from edited DataFrame
            updated_assessments = []
            for _, row in edited_df.iterrows():
                topics_list = [t.strip() for t in str(row.get("Topics", "")).split(",") if t.strip()]
                deadline_val = str(row.get("Deadline", "")).strip() or None
                updated_assessments.append(
                    AssessmentItem(
                        name=str(row["Name"]),
                        assessment_type=AssessmentType.from_string(str(row["Type"])),
                        deadline=deadline_val,
                        weight_percentage=float(row.get("Weight (%)", 0.0)),
                        topics=topics_list,
                        verification_status=VerificationStatus.CONFIRMED_BY_USER,
                        confidence_score=1.0,
                    )
                )

            course_meta = CourseMetadata(
                course_name=c_name,
                course_code=c_code or None,
                instructor_name=c_instructor or None,
                semester_start=sem_start or None,
                semester_end=sem_end or None,
                study_hours_recommended_per_week=rec_hours,
                raw_syllabus_text=current_extracted.course.raw_syllabus_text,
                topics=current_extracted.course.topics,
            )

            course_id = course_repo.save_course(course_meta)
            course_repo.save_assessments(course_id, updated_assessments)

            st.success(f"🎉 Successfully saved **{c_name}** with {len(updated_assessments)} assessments!")
            st.session_state["active_course_id"] = course_id
            st.info("Next step: Head over to **Study Planner** in the sidebar to generate your weekly schedule!")
