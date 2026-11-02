"""Calendar Export Service generating RFC 5545 compliant ICS files for Google Calendar."""
from datetime import datetime, date, time
from typing import List, Optional
import icalendar
from icalendar import Calendar, Event, vText
import zoneinfo

from models.schemas import StudySession, AssessmentItem, StudyPlan


class CalendarExporter:
    """Exports study sessions and assessment deadlines into valid .ics files compatible with Google Calendar."""

    def __init__(self, default_timezone: str = "Europe/Riga"):
        self.default_timezone = default_timezone

    def export_plan_to_ics(
        self,
        plan: StudyPlan,
        assessments: Optional[List[AssessmentItem]] = None,
        include_deadlines: bool = True,
    ) -> bytes:
        """Generates an RFC 5545 ICS calendar byte string from a study plan."""
        tz_name = plan.preferences.timezone or self.default_timezone
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
        except Exception:
            tz = zoneinfo.ZoneInfo("UTC")
            tz_name = "UTC"

        cal = Calendar()
        cal.add("prodid", "-//SyllabusPilot//Study Planning Agent//EN")
        cal.add("version", "2.0")
        cal.add("calscale", "GREGORIAN")
        cal.add("method", "PUBLISH")
        cal.add("x-wr-calname", f"{plan.course_name} - Study Schedule")
        cal.add("x-wr-timezone", tz_name)

        now = datetime.now(tz)

        # 1. Add Study Sessions as Events
        for session in plan.sessions:
            event = Event()
            
            # Title
            prefix = "[Revision]" if session.is_revision else "[Study]"
            summary = f"{prefix} {session.course_name}: {session.topic}"
            event.add("summary", summary)

            # Datetime parsing
            s_date = datetime.strptime(session.session_date, "%Y-%m-%d").date()
            s_start_h, s_start_m = map(int, session.start_time.split(":"))
            s_end_h, s_end_m = map(int, session.end_time.split(":"))

            start_dt = datetime.combine(s_date, time(s_start_h, s_start_m), tzinfo=tz)
            end_dt = datetime.combine(s_date, time(s_end_h, s_end_m), tzinfo=tz)

            event.add("dtstart", start_dt)
            event.add("dtend", end_dt)
            event.add("dtstamp", now)

            # Metadata Description
            desc_lines = [
                f"Course: {session.course_name}",
                f"Target Assessment: {session.assessment_name}",
                f"Topic: {session.topic}",
                f"Duration: {session.duration_hours} hours",
                f"Revision Session: {'Yes' if session.is_revision else 'No'}",
                f"Status: {'Completed' if session.is_completed else 'Scheduled'}",
            ]
            if session.notes:
                desc_lines.append(f"Notes: {session.notes}")
            desc_lines.append("\nExported via SyllabusPilot (GDG Riga AI Agents Hackathon)")
            event.add("description", "\n".join(desc_lines))

            # UID & Categories
            event.add("uid", f"{session.session_uid}@syllabus-pilot.app")
            event.add("status", "CONFIRMED")
            event.add("categories", ["Study", session.course_name])

            cal.add_component(event)

        # 2. Add Assessment Deadlines if requested
        if include_deadlines and assessments:
            for a in assessments:
                if not a.deadline:
                    continue
                try:
                    d_event = Event()
                    d_date = datetime.strptime(a.deadline[:10], "%Y-%m-%d").date()
                    d_dt = datetime.combine(d_date, time(23, 59), tzinfo=tz)

                    d_event.add("summary", f"[DEADLINE] {plan.course_name}: {a.name}")
                    d_event.add("dtstart", d_dt)
                    d_event.add("dtend", d_dt)
                    d_event.add("dtstamp", now)

                    desc = (
                        f"Assessment: {a.name}\n"
                        f"Type: {a.assessment_type.value if hasattr(a.assessment_type, 'value') else a.assessment_type}\n"
                        f"Grading Weight: {a.weight_percentage or 0}%\n"
                        f"Description: {a.description or 'No extra notes'}\n"
                    )
                    d_event.add("description", desc)
                    d_event.add("uid", f"deadline-{a.id or a.name.replace(' ', '_')}@syllabus-pilot.app")
                    d_event.add("priority", 1)  # Highest priority
                    d_event.add("categories", ["Deadline", plan.course_name])

                    cal.add_component(d_event)
                except Exception:
                    continue

        return cal.to_ical()
