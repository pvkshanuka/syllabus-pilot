"""Unit tests for Calendar Export service."""
import pytest
import icalendar
from services.calendar_export import CalendarExporter
from models.schemas import (
    StudyPlan,
    StudySession,
    StudyPreferences,
    AssessmentItem,
    AssessmentType,
)


@pytest.fixture
def sample_plan():
    prefs = StudyPreferences(
        hours_per_week=10.0,
        available_days=["Monday", "Wednesday"],
        preferred_time_of_day="Evening",
        timezone="Europe/Riga",
    )
    sessions = [
        StudySession(
            course_name="Data Structures",
            assessment_name="Midterm 1",
            topic="Binary Trees",
            session_date="2026-10-12",
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
            is_revision=False,
        ),
        StudySession(
            course_name="Data Structures",
            assessment_name="Midterm 1",
            topic="Review & Practice",
            session_date="2026-10-14",
            start_time="18:30",
            end_time="20:00",
            duration_hours=1.5,
            is_revision=True,
        ),
    ]
    return StudyPlan(
        course_id=1,
        course_name="Data Structures",
        total_planned_hours=3.0,
        preferences=prefs,
        sessions=sessions,
    )


def test_calendar_export_valid_ics(sample_plan):
    exporter = CalendarExporter()
    assessments = [
        AssessmentItem(
            id=101,
            name="Midterm 1",
            assessment_type=AssessmentType.MIDTERM,
            deadline="2026-10-15",
            weight_percentage=20.0,
        )
    ]

    ics_bytes = exporter.export_plan_to_ics(sample_plan, assessments=assessments)
    assert ics_bytes is not None
    assert b"BEGIN:VCALENDAR" in ics_bytes
    assert b"END:VCALENDAR" in ics_bytes

    # Parse back using icalendar
    cal = icalendar.Calendar.from_ical(ics_bytes)
    assert cal.get("prodid") is not None
    
    events = [c for c in cal.subcomponents if c.name == "VEVENT"]
    assert len(events) == 3  # 2 study sessions + 1 deadline

    # Check session event
    session_event = [e for e in events if "Binary Trees" in str(e.get("summary"))][0]
    assert session_event.get("dtstart") is not None
    assert session_event.get("dtend") is not None
    assert "syllabus-pilot" in str(session_event.get("uid"))
    assert "Data Structures" in str(session_event.get("description"))

    # Check deadline event
    deadline_event = [e for e in events if "[DEADLINE]" in str(e.get("summary"))][0]
    assert "Midterm 1" in str(deadline_event.get("summary"))
