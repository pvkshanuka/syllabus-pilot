"""Unit tests for Deterministic Study Scheduler."""
from datetime import date, datetime
import pytest
from services.scheduling import StudyScheduler
from models.schemas import AssessmentItem, AssessmentType, StudyPreferences


@pytest.fixture
def sample_assessments():
    return [
        AssessmentItem(
            name="Assignment 1",
            assessment_type=AssessmentType.ASSIGNMENT,
            deadline="2026-10-15",
            weight_percentage=10.0,
            topics=["Basic Control Flow", "Functions"],
        ),
        AssessmentItem(
            name="Midterm Exam",
            assessment_type=AssessmentType.MIDTERM,
            deadline="2026-11-05",
            weight_percentage=25.0,
            topics=["OOP", "Data Structures"],
        ),
        AssessmentItem(
            name="Final Project",
            assessment_type=AssessmentType.PROJECT,
            deadline="2026-12-10",
            weight_percentage=30.0,
            topics=["System Design", "Database Integration"],
        ),
    ]


def test_schedule_generation_respects_constraints(sample_assessments):
    scheduler = StudyScheduler()
    prefs = StudyPreferences(
        hours_per_week=10.0,
        available_days=["Tuesday", "Thursday", "Saturday"],
        preferred_time_of_day="Evening",
        session_duration_hours=1.5,
    )
    ref_date = date(2026, 9, 15)

    plan = scheduler.generate_plan(
        course_id=1,
        course_name="Computer Science 101",
        assessments=sample_assessments,
        preferences=prefs,
        reference_date=ref_date,
    )

    assert plan is not None
    assert len(plan.sessions) > 0
    assert plan.total_planned_hours > 0

    allowed_days = {"Tuesday", "Thursday", "Saturday"}
    for session in plan.sessions:
        s_date = datetime.strptime(session.session_date, "%Y-%m-%d").date()
        # 1. No sessions in past
        assert s_date >= ref_date
        # 2. Available days respect
        assert s_date.strftime("%A") in allowed_days

    # 3. Sessions strictly before deadlines
    for a in sample_assessments:
        a_deadline = datetime.strptime(a.deadline, "%Y-%m-%d").date()
        a_sessions = [s for s in plan.sessions if s.assessment_name == a.name]
        for s in a_sessions:
            s_date = datetime.strptime(s.session_date, "%Y-%m-%d").date()
            assert s_date < a_deadline


def test_no_overlapping_session_times(sample_assessments):
    scheduler = StudyScheduler()
    prefs = StudyPreferences(
        hours_per_week=20.0,
        available_days=["Monday"],  # force multiple sessions on same day
        preferred_time_of_day="Morning",
        session_duration_hours=1.5,
    )
    ref_date = date(2026, 9, 1)

    plan = scheduler.generate_plan(
        course_id=1,
        course_name="Computer Science 101",
        assessments=sample_assessments,
        preferences=prefs,
        reference_date=ref_date,
    )

    # Check same-date sessions have distinct non-overlapping intervals
    sessions_by_date = {}
    for s in plan.sessions:
        sessions_by_date.setdefault(s.session_date, []).append(s)

    for d, s_list in sessions_by_date.items():
        if len(s_list) > 1:
            for i in range(len(s_list) - 1):
                end_cur = s_list[i].end_time
                start_next = s_list[i + 1].start_time
                assert end_cur <= start_next


def test_revision_session_included_for_exam(sample_assessments):
    scheduler = StudyScheduler()
    prefs = StudyPreferences(
        available_days=["Monday", "Wednesday", "Friday"],
        preferred_time_of_day="Evening",
    )
    plan = scheduler.generate_plan(
        course_id=1,
        course_name="CS101",
        assessments=sample_assessments,
        preferences=prefs,
        reference_date=date(2026, 9, 1),
    )

    midterm_sessions = [s for s in plan.sessions if s.assessment_name == "Midterm Exam"]
    assert len(midterm_sessions) > 0
    # Final session before exam should be revision
    assert midterm_sessions[-1].is_revision is True
