"""Unit tests for SQLite database initialization and repositories."""
import os
import tempfile
import pytest
from models.database import init_db, get_connection
from models.schemas import (
    CourseMetadata,
    AssessmentItem,
    AssessmentType,
    VerificationStatus,
    StudyPreferences,
    StudyPlan,
    StudySession,
)
from repositories.course_repository import CourseRepository
from repositories.study_repository import StudyRepository


@pytest.fixture
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    yield path
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def test_course_crud(temp_db):
    repo = CourseRepository(temp_db)
    course = CourseMetadata(
        course_name="Computer Systems",
        course_code="CS202",
        instructor_name="Prof. Turing",
        semester_start="2026-09-01",
        semester_end="2026-12-20",
        study_hours_recommended_per_week=8.0,
        topics=["Memory", "Pipelines", "Assembly"],
    )
    course_id = repo.save_course(course)
    assert course_id > 0

    fetched = repo.get_course(course_id)
    assert fetched is not None
    assert fetched.course_name == "Computer Systems"
    assert fetched.course_code == "CS202"
    assert "Assembly" in fetched.topics

    courses = repo.list_courses()
    assert len(courses) == 1


def test_assessment_crud(temp_db):
    course_repo = CourseRepository(temp_db)
    course_id = course_repo.save_course(
        CourseMetadata(course_name="Data Structures", course_code="CS102")
    )

    assessments = [
        AssessmentItem(
            name="Assignment 1",
            assessment_type=AssessmentType.ASSIGNMENT,
            deadline="2026-10-01",
            weight_percentage=15.0,
            topics=["Arrays", "Linked Lists"],
            verification_status=VerificationStatus.VERIFIED,
        ),
        AssessmentItem(
            name="Final Exam",
            assessment_type=AssessmentType.FINAL,
            deadline="2026-12-15",
            weight_percentage=40.0,
            topics=["All"],
            verification_status=VerificationStatus.CONFIRMED_BY_USER,
        ),
    ]

    saved = course_repo.save_assessments(course_id, assessments)
    assert len(saved) == 2
    assert saved[0].id is not None

    fetched = course_repo.get_assessments(course_id)
    assert len(fetched) == 2
    assert fetched[0].name == "Assignment 1"
    assert fetched[0].weight_percentage == 15.0
    assert fetched[1].assessment_type == AssessmentType.FINAL


def test_study_plan_and_sessions(temp_db):
    course_repo = CourseRepository(temp_db)
    study_repo = StudyRepository(temp_db)

    c_id = course_repo.save_course(CourseMetadata(course_name="AI Systems", course_code="AI401"))

    prefs = StudyPreferences(
        hours_per_week=12.0,
        available_days=["Monday", "Wednesday", "Friday"],
        preferred_time_of_day="Evening",
    )

    sessions = [
        StudySession(
            course_name="AI Systems",
            assessment_name="Midterm Exam",
            topic="Search Algorithms",
            session_date="2026-09-15",
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
        ),
        StudySession(
            course_name="AI Systems",
            assessment_name="Midterm Exam",
            topic="Heuristic Search",
            session_date="2026-09-17",
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
        ),
    ]

    plan = StudyPlan(
        course_id=c_id,
        course_name="AI Systems",
        total_planned_hours=3.0,
        preferences=prefs,
        sessions=sessions,
    )

    plan_id = study_repo.save_plan(plan)
    assert plan_id > 0

    fetched_plan = study_repo.get_plan(plan_id)
    assert fetched_plan is not None
    assert len(fetched_plan.sessions) == 2

    # Toggle completion
    session_id = fetched_plan.sessions[0].id
    study_repo.update_session_completion(session_id, True, "Completed all reading exercises")

    metrics = study_repo.get_progress_metrics(plan_id)
    assert metrics["completed_sessions"] == 1
    assert metrics["completed_hours"] == 1.5
    assert metrics["remaining_hours"] == 1.5
    assert metrics["progress_percentage"] == 50.0
