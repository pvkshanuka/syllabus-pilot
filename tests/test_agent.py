"""Unit tests for SyllabusPilotAgent and registered tools."""
import os
from datetime import date
import tempfile
import pytest
from agent.agent import SyllabusPilotAgent
from agent.tools import SyllabusPilotTools
from models.database import init_db
from models.schemas import CourseMetadata, AssessmentItem, AssessmentType


@pytest.fixture
def temp_agent_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def test_agent_tools_execution(temp_agent_db):
    tools = SyllabusPilotTools(db_path=temp_agent_db, api_key=None)

    # 1. Extract syllabus text
    sample_path = os.path.join(os.path.dirname(__file__), "..", "samples", "sample_cs101_syllabus.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        text = f.read()

    res_extract = tools.extract_syllabus_information(text)
    assert res_extract["course_id"] > 0
    c_id = res_extract["course_id"]

    # 2. Validate extracted deadlines
    res_val = tools.validate_extracted_deadlines(c_id)
    assert res_val["total_assessments"] >= 5

    # 3. Generate study plan (3 questions: 12 hrs, Mon/Wed/Fri, Evening, start_date=2026-09-07)
    res_plan = tools.generate_study_plan(
        course_id=c_id,
        hours_per_week=12.0,
        available_days=["Monday", "Wednesday", "Friday"],
        preferred_time_of_day="Evening",
        start_date="2026-09-07",
    )
    assert res_plan["plan_id"] > 0
    assert res_plan["total_sessions"] > 0
    p_id = res_plan["plan_id"]

    # 4. Calculate priorities
    res_priorities = tools.calculate_workload_priorities(c_id)
    assert len(res_priorities["priorities"]) >= 5

    # 5. Export calendar
    ics_bytes = tools.export_calendar_events(p_id)
    assert b"BEGIN:VCALENDAR" in ics_bytes

    # 6. Track progress
    sessions = tools.study_repo.get_sessions_for_plan(p_id)
    res_prog = tools.track_study_progress(p_id, session_id=sessions[0].id, mark_done=True)
    assert res_prog["metrics"]["completed_sessions"] == 1

    # 7. Practice questions
    quiz = tools.generate_practice_questions("CS101", "Recursion", count=2)
    assert len(quiz) >= 1


def test_agent_message_handling(temp_agent_db):
    agent = SyllabusPilotAgent(db_path=temp_agent_db, api_key=None)

    # Seed a course and plan with future deadline
    c_id = agent.tools.course_repo.save_course(
        CourseMetadata(course_name="Algorithms", course_code="CS201")
    )
    agent.tools.course_repo.save_assessments(
        c_id,
        [
            AssessmentItem(
                name="Final Examination",
                assessment_type=AssessmentType.FINAL,
                deadline="2026-12-15",
                weight_percentage=35.0,
            )
        ],
    )
    res_plan = agent.tools.generate_study_plan(
        course_id=c_id,
        hours_per_week=10.0,
        start_date="2026-11-03",
    )
    p_id = res_plan["plan_id"]

    # Contextual triggers
    reply_priorities = agent.handle_message("What are my priorities?", context={"course_id": c_id})
    assert "Priorities" in reply_priorities

    reply_next = agent.handle_message("What should I study next?", context={"course_id": c_id, "plan_id": p_id})
    assert "Recommended Study Session" in reply_next

    reply_replan = agent.handle_message("I was sick and missed my study sessions", context={"course_id": c_id, "plan_id": p_id})
    assert "Adaptive Recovery" in reply_replan
