"""Unit tests for Smart Priority & Workload Balancer."""
from datetime import date
import pytest
from services.priority import WorkloadBalancer
from models.schemas import (
    AssessmentItem,
    AssessmentType,
    StudyPlan,
    StudySession,
    StudyPreferences,
)


def test_priority_calculation():
    balancer = WorkloadBalancer()
    ref_date = date(2026, 10, 1)

    assessments = [
        # Imminent deadline (4 days) + heavy weight (30%) -> High Priority
        AssessmentItem(
            name="Midterm 1",
            assessment_type=AssessmentType.MIDTERM,
            deadline="2026-10-05",
            weight_percentage=30.0,
        ),
        # Far deadline (70 days) + low weight (5%) -> Low Priority
        AssessmentItem(
            name="Pop Quiz",
            assessment_type=AssessmentType.QUIZ,
            deadline="2026-12-10",
            weight_percentage=5.0,
        ),
    ]

    priorities = balancer.calculate_priorities(assessments, reference_date=ref_date)
    assert len(priorities) == 2

    high_p = [p for p in priorities if p.assessment_name == "Midterm 1"][0]
    low_p = [p for p in priorities if p.assessment_name == "Pop Quiz"][0]

    assert high_p.priority_score > low_p.priority_score
    assert high_p.priority_tier == "High"
    assert low_p.priority_tier == "Low"


def test_workload_overload_detection():
    balancer = WorkloadBalancer()
    prefs = StudyPreferences(hours_per_week=4.0)  # low weekly limit

    # Create 3 sessions on same week totaling 4.5 hours -> Exceeds 4.0 limit
    sessions = [
        StudySession(
            course_name="CS101",
            assessment_name="Midterm 1",
            topic="Trees",
            session_date="2026-10-12",  # Monday
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
        ),
        StudySession(
            course_name="CS101",
            assessment_name="Midterm 1",
            topic="Graphs",
            session_date="2026-10-14",  # Wednesday
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
        ),
        StudySession(
            course_name="CS101",
            assessment_name="Midterm 1",
            topic="Dynamic Programming",
            session_date="2026-10-16",  # Friday
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
        ),
    ]

    plan = StudyPlan(
        course_id=1,
        course_name="CS101",
        total_planned_hours=4.5,
        preferences=prefs,
        sessions=sessions,
    )

    summary = balancer.analyze_workload(plan)
    assert len(summary.overloaded_weeks) >= 1
    assert summary.overloaded_weeks[0].planned_hours == 4.5
    assert len(summary.recommendations) >= 1
    assert "exceeds available study capacity" in summary.recommendations[0]
