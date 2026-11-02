"""End-to-End integration test covering the complete SyllabusPilot lifecycle."""
import os
import tempfile
from datetime import date
import pytest
import icalendar

from models.database import init_db
from models.schemas import AssessmentType, VerificationStatus, StudyPreferences
from repositories.course_repository import CourseRepository
from repositories.study_repository import StudyRepository
from services.extraction import SyllabusExtractor
from services.scheduling import StudyScheduler
from services.priority import WorkloadBalancer
from services.replanning import AdaptiveRecoveryEngine
from services.calendar_export import CalendarExporter
from services.study_coach import StudyCoachService
from agent.agent import SyllabusPilotAgent


@pytest.fixture
def clean_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def test_complete_syllabus_pilot_lifecycle(clean_db):
    course_repo = CourseRepository(clean_db)
    study_repo = StudyRepository(clean_db)
    extractor = SyllabusExtractor(api_key=None)
    scheduler = StudyScheduler()
    balancer = WorkloadBalancer(scheduler)
    recovery_engine = AdaptiveRecoveryEngine(scheduler)
    exporter = CalendarExporter()
    coach = StudyCoachService(api_key=None)

    # 1. Load syllabus
    sample_path = os.path.join(os.path.dirname(__file__), "..", "samples", "sample_datascience_syllabus.txt")
    with open(sample_path, "r", encoding="utf-8") as f:
        syllabus_text = f.read()

    # 2. Extract entities
    extracted = extractor.extract_from_text(syllabus_text)
    assert extracted.course is not None
    assert len(extracted.assessments) >= 4

    # 3. Save course and assessments to DB
    course_id = course_repo.save_course(extracted.course)
    saved_assessments = course_repo.save_assessments(course_id, extracted.assessments)
    assert course_id > 0
    assert len(saved_assessments) == len(extracted.assessments)

    # 4. User edits an assessment in table
    first_item = saved_assessments[0]
    first_item.weight_percentage = 10.0
    first_item.verification_status = VerificationStatus.CONFIRMED_BY_USER
    updated_ok = course_repo.update_assessment(first_item)
    assert updated_ok is True

    # 5. Answer 3 questions & Generate Study Plan
    prefs = StudyPreferences(
        hours_per_week=12.0,
        available_days=["Tuesday", "Thursday", "Saturday"],
        preferred_time_of_day="Evening",
        start_date="2026-09-02",
    )
    plan = scheduler.generate_plan(
        course_id=course_id,
        course_name=extracted.course.course_name,
        assessments=saved_assessments,
        preferences=prefs,
    )
    plan_id = study_repo.save_plan(plan)
    assert plan_id > 0
    assert len(plan.sessions) > 0

    # 6. Export Calendar (.ics)
    ics_bytes = exporter.export_plan_to_ics(plan, assessments=saved_assessments)
    assert b"BEGIN:VCALENDAR" in ics_bytes
    cal = icalendar.Calendar.from_ical(ics_bytes)
    events = [e for e in cal.subcomponents if e.name == "VEVENT"]
    assert len(events) >= len(plan.sessions)

    # 7. Progress tracking: Complete first 2 sessions
    plan_sessions = study_repo.get_sessions_for_plan(plan_id)
    study_repo.update_session_completion(plan_sessions[0].id, True, "Mastered NumPy array broadcasting")
    study_repo.update_session_completion(plan_sessions[1].id, True, "Finished Pandas dataframes lab")

    metrics = study_repo.get_progress_metrics(plan_id)
    assert metrics["completed_sessions"] == 2
    assert metrics["completed_hours"] > 0
    assert metrics["progress_percentage"] > 0

    # 8. Adaptive Recovery: Simulate missed session
    fresh_plan = study_repo.get_plan(plan_id)
    missed_date = fresh_plan.sessions[2].session_date
    proposal = recovery_engine.propose_recovery(
        current_plan=fresh_plan,
        current_date=date(2026, 9, 20),
        missed_dates=[missed_date],
        reason="Had food poisoning for 2 days",
        assessments=saved_assessments,
    )
    assert len(proposal.missed_sessions) >= 1
    assert len(proposal.completed_sessions) == 2  # Preserved!
    # Apply recovery
    study_repo.replace_sessions(plan_id, proposal.redistributed_sessions)

    # 9. Priority & Workload Balancer
    updated_sessions = study_repo.get_sessions_for_plan(plan_id)
    priorities = balancer.calculate_priorities(saved_assessments, updated_sessions)
    assert len(priorities) == len(saved_assessments)
    assert priorities[0].priority_score >= priorities[-1].priority_score

    # 10. AI Study Coach: Next session & Practice questions
    updated_plan = study_repo.get_plan(plan_id)
    next_s = coach.suggest_next_session(updated_plan)
    assert next_s is not None
    assert next_s.is_completed is False

    quiz = coach.generate_practice_questions("Data Science", "Regression Models", count=2)
    assert len(quiz) == 2
    assert quiz[0].correct_answer_index >= 0

    # 11. Agent Message handling
    agent = SyllabusPilotAgent(db_path=clean_db, api_key=None)
    response = agent.handle_message(
        "I was sick and missed my study sessions",
        context={"course_id": course_id, "plan_id": plan_id},
    )
    assert "Adaptive Recovery" in response
