"""AI Study Coach, Smart Priority Balancer, and Practice Quiz UI."""
from datetime import date
import pandas as pd
import streamlit as st
from repositories.course_repository import CourseRepository
from repositories.study_repository import StudyRepository
from services.priority import WorkloadBalancer
from services.study_coach import StudyCoachService
from agent.agent import SyllabusPilotAgent


def render_coach_page(course_repo: CourseRepository, study_repo: StudyRepository):
    """Renders the AI Study Coach, Workload Balancer, and Practice Quiz."""
    st.markdown("## 💡 AI Study Coach & Workload Balancer")
    st.markdown(
        "Your autonomous academic advisor powered by Gemini. Prioritize deadlines, balance weekly study loads, "
        "and test your knowledge with active recall quizzes directly tied to your syllabus topics."
    )

    courses = course_repo.list_courses()
    if not courses:
        st.warning("Please upload a course syllabus first.")
        return

    course_options = {f"{c.course_name} ({c.course_code or 'No Code'})": c.id for c in courses}
    selected_lbl = st.selectbox("Select Course for Coaching:", list(course_options.keys()))
    course_id = course_options[selected_lbl]

    course = course_repo.get_course(course_id)
    assessments = course_repo.get_assessments(course_id)
    plan = study_repo.get_active_plan_for_course(course_id)

    tab_coach, tab_priority, tab_quiz = st.tabs([
        "🤖 Chat with SyllabusPilotAgent",
        "⚖️ Smart Priority & Workload Balancer",
        "🎯 Topic Practice Quiz",
    ])

    # TAB 1: Conversational AI Coach
    with tab_coach:
        st.markdown("### 💬 Ask SyllabusPilotAgent")
        st.markdown("Ask anything about your study priorities, exam preparation, or what topic to focus on next.")

        if "chat_messages" not in st.session_state:
            st.session_state["chat_messages"] = [
                {"role": "assistant", "content": "Hi! I am **SyllabusPilotAgent**. How can I help you optimize your study routine today?"}
            ]

        # Display Chat History
        for msg in st.session_state["chat_messages"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        # Quick action prompt buttons
        q1, q2, q3 = st.columns(3)
        quick_input = None
        with q1:
            if st.button("❓ What should I study next?"):
                quick_input = "What should I study next?"
        with q2:
            if st.button("🎯 Show my highest priorities"):
                quick_input = "What are my highest priorities?"
        with q3:
            if st.button("🔄 I was sick, please replan"):
                quick_input = "I was sick for three days and missed my study sessions"

        user_input = st.chat_input("Type your study question or request here...") or quick_input

        if user_input:
            st.session_state["chat_messages"].append({"role": "user", "content": user_input})
            with st.chat_message("user"):
                st.markdown(user_input)

            agent = SyllabusPilotAgent(db_path=course_repo.db_path)
            context = {"course_id": course_id, "plan_id": plan.id if plan else None}
            
            with st.chat_message("assistant"):
                with st.spinner("SyllabusPilotAgent is thinking..."):
                    response = agent.handle_message(user_input, context=context)
                    st.markdown(response)
                    st.session_state["chat_messages"].append({"role": "assistant", "content": response})

    # TAB 2: Smart Priority & Workload Balancer
    with tab_priority:
        st.markdown("### ⚖️ Multi-Factor Priority & Weekly Workload Analysis")
        st.markdown(
            "Priority scores (0-100) are computed dynamically from **deadline proximity**, **grading weight**, "
            "**estimated study effort**, and **your completed progress**."
        )

        balancer = WorkloadBalancer()
        priorities = balancer.calculate_priorities(assessments, plan.sessions if plan else [])
        
        # Display Priorities Table
        p_rows = []
        for p in priorities:
            p_rows.append({
                "Tier": p.priority_tier,
                "Score": p.priority_score,
                "Assessment": p.assessment_name,
                "Deadline": p.deadline or "TBA",
                "Weight": f"{p.weight_percentage}%",
                "Est. Hours": f"{p.estimated_effort_hours}h",
                "Completed": f"{p.progress_percentage:.0f}%",
                "Explanation": p.explanation,
            })
        st.dataframe(pd.DataFrame(p_rows), use_container_width=True)

        st.write("---")
        st.markdown("#### 📈 Weekly Workload Capacity & Overload Detection")

        if plan:
            summary = balancer.analyze_workload(plan, assessments)
            col_w1, col_w2, col_w3 = st.columns(3)
            with col_w1:
                st.metric("Total Planned Hours", f"{summary.total_planned_hours}h")
            with col_w2:
                st.metric("Total Term Capacity", f"{summary.total_available_hours}h")
            with col_w3:
                st.metric("Overloaded Weeks Detected", len(summary.overloaded_weeks))

            if summary.overloaded_weeks:
                st.error("🚨 Overloaded Study Weeks Detected!")
                for rec in summary.recommendations:
                    st.warning(f"👉 {rec}")
            else:
                st.success("✅ Workload is healthy! No weeks exceed your weekly hour capacity.")

            # Week-by-Week Breakdown
            if summary.overloaded_weeks:
                st.markdown("##### Overloaded Weeks Detail")
                overload_data = [
                    {
                        "Week": f"{w.week_start} to {w.week_end}",
                        "Planned (h)": w.planned_hours,
                        "Capacity (h)": w.available_hours,
                        "Assessments Due": ", ".join(w.assessments_due),
                    }
                    for w in summary.overloaded_weeks
                ]
                st.table(pd.DataFrame(overload_data))
        else:
            st.info("Generate a study plan first to analyze weekly workload capacity.")

    # TAB 3: Practice Quiz Generator
    with tab_quiz:
        st.markdown("### 🎯 Active Recall Practice Quiz")
        st.markdown(
            "Test your comprehension on syllabus topics. Practice quizzes are generated from your course syllabus "
            "topics with instant pedagogical feedback and explanations."
        )

        all_topics = course.topics or ["General Fundamentals", "Core Concepts", "Advanced Applications"]
        selected_topic = st.selectbox("Select Syllabus Topic:", all_topics)

        coach_service = StudyCoachService()

        if st.button("🚀 Generate 3 Practice Questions", key="btn_gen_quiz", type="primary"):
            with st.spinner(f"Generating practice questions on '{selected_topic}' with Gemini..."):
                questions = coach_service.generate_practice_questions(course.course_name, selected_topic, count=3)
                st.session_state["quiz_questions"] = questions
                st.session_state["quiz_submitted"] = False

        quiz_questions = st.session_state.get("quiz_questions")
        if quiz_questions:
            st.write("---")
            st.markdown(f"#### Quiz: **{selected_topic}**")

            user_answers = {}
            for i, q in enumerate(quiz_questions):
                st.markdown(f"**Question {i+1}**: {q.question}")
                ans = st.radio(
                    f"Choose answer for Q{i+1}:",
                    options=range(len(q.options)),
                    format_func=lambda idx, opts=q.options: opts[idx],
                    key=f"quiz_radio_{i}",
                )
                user_answers[i] = ans
                st.write("")

            if st.button("Submit Quiz Answers", type="primary"):
                score = 0
                for i, q in enumerate(quiz_questions):
                    chosen = user_answers[i]
                    is_correct = chosen == q.correct_answer_index
                    if is_correct:
                        score += 1
                        st.success(f"**Q{i+1} Correct!** 🎉 {q.options[q.correct_answer_index]}\n\n*Explanation:* {q.explanation}")
                    else:
                        st.error(f"**Q{i+1} Incorrect.** You selected '{q.options[chosen]}'. Correct answer: **{q.options[q.correct_answer_index]}**\n\n*Explanation:* {q.explanation}")
                
                final_pct = (score / len(quiz_questions)) * 100
                st.info(f"🏆 Final Score: **{score}/{len(quiz_questions)}** ({final_pct:.0f}%)")
