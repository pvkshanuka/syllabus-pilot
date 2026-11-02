"""Unit tests for Adaptive Study Recovery Engine."""
from datetime import date
import pytest
from services.replanning import AdaptiveRecoveryEngine
from models.schemas import (
    StudyPlan,
    StudySession,
    StudyPreferences,
    AssessmentItem,
    AssessmentType,
)


@pytest.fixture
def plan_with_missed_sessions():
    prefs = StudyPreferences(
        hours_per_week=10.0,
        available_days=["Monday", "Wednesday", "Friday"],
        preferred_time_of_day="Evening",
    )
    # Today simulated as 2026-10-15
    sessions = [
        # Session 1: completed in past
        StudySession(
            course_name="CS101",
            assessment_name="Midterm 1",
            topic="Functions",
            session_date="2026-10-05",
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
            is_completed=True,
        ),
        # Session 2: missed in past (is_completed=False, date < today)
        StudySession(
            course_name="CS101",
            assessment_name="Midterm 1",
            topic="Recursion",
            session_date="2026-10-07",
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
            is_completed=False,
        ),
        # Session 3: missed in past
        StudySession(
            course_name="CS101",
            assessment_name="Midterm 1",
            topic="Complexity",
            session_date="2026-10-09",
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
            is_completed=False,
        ),
        # Session 4: future session
        StudySession(
            course_name="CS101",
            assessment_name="Midterm 1",
            topic="Exam Review",
            session_date="2026-10-19",
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
            is_completed=False,
            is_revision=True,
        ),
    ]
    return StudyPlan(
        course_id=1,
        course_name="CS101",
        total_planned_hours=6.0,
        preferences=prefs,
        sessions=sessions,
    )


def test_adaptive_recovery_preserves_completed_and_redistributes(plan_with_missed_sessions):
    engine = AdaptiveRecoveryEngine()
    current_date = date(2026, 10, 15)
    assessments = [
        AssessmentItem(
            name="Midterm 1",
            assessment_type=AssessmentType.MIDTERM,
            deadline="2026-10-25",
            weight_percentage=20.0,
        )
    ]

    proposal = engine.propose_recovery(
        current_plan=plan_with_missed_sessions,
        current_date=current_date,
        reason="Flu illness for 3 days",
        assessments=assessments,
    )

    assert proposal is not None
    assert len(proposal.missed_sessions) == 2
    assert len(proposal.completed_sessions) == 1
    assert proposal.completed_sessions[0].topic == "Functions"

    # All redistributed sessions must be on or after current_date (except preserved completed)
    for s in proposal.redistributed_sessions:
        if s.is_completed:
            continue
        assert s.session_date >= "2026-10-15"

    # Explanation mentions recovered count and illness reason
    assert "Flu illness for 3 days" in proposal.explanation
    assert "2 missed" in proposal.explanation or "2" in proposal.explanation
