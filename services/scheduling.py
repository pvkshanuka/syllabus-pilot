"""Deterministic Study Planning Engine for SyllabusPilot."""
from datetime import datetime, date, timedelta
from typing import List, Optional, Tuple, Dict
from models.schemas import (
    AssessmentItem,
    AssessmentType,
    StudyPreferences,
    StudySession,
    StudyPlan,
)


class StudyScheduler:
    """Generates conflict-free, realistic study schedules respecting deadlines and availability."""

    TIME_BLOCK_MAPPINGS = {
        "Morning": ("09:00", "10:30"),
        "Afternoon": ("14:00", "15:30"),
        "Evening": ("18:30", "20:00"),
        "Night": ("20:30", "22:00"),
    }

    DAY_NAME_TO_INT = {
        "Monday": 0,
        "Tuesday": 1,
        "Wednesday": 2,
        "Thursday": 3,
        "Friday": 4,
        "Saturday": 5,
        "Sunday": 6,
    }

    def __init__(self):
        pass

    def estimate_effort_hours(self, assessment: AssessmentItem) -> float:
        """Estimates required study hours based on assessment type and grading weight."""
        weight = assessment.weight_percentage if assessment.weight_percentage is not None else 10.0
        a_type = assessment.assessment_type

        # Multiplier depending on assessment nature
        if a_type in (AssessmentType.FINAL, AssessmentType.EXAM):
            factor = 1.0
            base = 6.0
        elif a_type == AssessmentType.MIDTERM:
            factor = 0.8
            base = 4.0
        elif a_type == AssessmentType.PROJECT:
            factor = 0.9
            base = 5.0
        elif a_type in (AssessmentType.ASSIGNMENT, AssessmentType.LAB):
            factor = 0.6
            base = 3.0
        elif a_type == AssessmentType.QUIZ:
            factor = 0.3
            base = 1.5
        else:
            factor = 0.5
            base = 2.0

        estimated = base + (weight * factor)
        # Cap between 2.0 and 35.0 hours for a single assessment
        return round(min(max(estimated, 2.0), 35.0), 1)

    def generate_plan(
        self,
        course_id: int,
        course_name: str,
        assessments: List[AssessmentItem],
        preferences: StudyPreferences,
        reference_date: Optional[date] = None,
    ) -> StudyPlan:
        """Generates a complete, week-by-week deterministic study plan."""
        # 1. Determine plan start date
        today = reference_date or date.today()
        start_date = today
        if preferences.start_date:
            try:
                parsed_start = datetime.strptime(preferences.start_date, "%Y-%m-%d").date()
                start_date = parsed_start
            except ValueError:
                pass

        # 2. Filter assessments that have deadlines on or after start_date
        active_assessments = []
        warnings = []
        for a in assessments:
            if not a.deadline:
                warnings.append(f"Assessment '{a.name}' has no set deadline and was excluded from automatic scheduling.")
                continue
            try:
                deadline_date = datetime.strptime(a.deadline[:10], "%Y-%m-%d").date()
                if deadline_date < start_date:
                    warnings.append(f"Assessment '{a.name}' deadline ({a.deadline}) is in the past. Skipped.")
                    continue
                active_assessments.append((deadline_date, a))
            except ValueError:
                warnings.append(f"Invalid deadline format for '{a.name}' ({a.deadline}). Skipped.")

        # Sort assessments chronologically by deadline
        active_assessments.sort(key=lambda x: x[0])

        if not active_assessments:
            return StudyPlan(
                course_id=course_id,
                course_name=course_name,
                preferences=preferences,
                sessions=[],
                warnings=warnings or ["No upcoming deadlines found to schedule."],
                summary="No scheduled sessions created.",
            )

        # 3. Available days set
        pref_days_indices = set()
        for d in preferences.available_days:
            if d in self.DAY_NAME_TO_INT:
                pref_days_indices.add(self.DAY_NAME_TO_INT[d])
        if not pref_days_indices:
            pref_days_indices = {0, 2, 4}  # Mon, Wed, Fri fallback

        # 4. Preferred time slots
        start_t_str, end_t_str = self.TIME_BLOCK_MAPPINGS.get(
            preferences.preferred_time_of_day, ("18:30", "20:00")
        )
        duration = preferences.session_duration_hours

        # 5. Build candidate study slots across calendar
        max_deadline = active_assessments[-1][0]
        calendar_slots: List[date] = []
        curr = start_date
        while curr <= max_deadline:
            if curr.weekday() in pref_days_indices:
                calendar_slots.append(curr)
            curr += timedelta(days=1)

        # 6. Schedule sessions for each assessment
        all_sessions: List[StudySession] = []
        scheduled_by_date: Dict[date, List[str]] = {}  # date -> list of start_times

        for deadline_date, assessment in active_assessments:
            effort_hours = self.estimate_effort_hours(assessment)
            num_sessions = max(1, int(round(effort_hours / duration)))

            # Available slots strictly before deadline
            valid_slots = [d for d in calendar_slots if d < deadline_date]
            if not valid_slots:
                warnings.append(
                    f"Insufficient study slots before '{assessment.name}' deadline ({deadline_date})."
                )
                continue

            # Topic distribution
            topics = assessment.topics or ["Foundational Concepts", "Core Practice", "Comprehensive Review"]
            
            # Select slots backwards from deadline (spaced out)
            stride = max(1, len(valid_slots) // (num_sessions + 1))
            selected_dates = []
            idx = len(valid_slots) - 1
            while len(selected_dates) < num_sessions and idx >= 0:
                selected_dates.append(valid_slots[idx])
                idx -= stride

            selected_dates.reverse()  # chronological order

            # Create sessions
            for i, s_date in enumerate(selected_dates):
                is_revision = (i == len(selected_dates) - 1 and assessment.assessment_type in (
                    AssessmentType.EXAM, AssessmentType.MIDTERM, AssessmentType.FINAL
                ))
                topic = "Exam Revision & Practice" if is_revision else topics[i % len(topics)]

                # Avoid intra-day time conflict
                existing_times = scheduled_by_date.get(s_date, [])
                slot_start, slot_end = self._allocate_time_slot(
                    start_t_str, duration, len(existing_times)
                )
                if s_date not in scheduled_by_date:
                    scheduled_by_date[s_date] = []
                scheduled_by_date[s_date].append(slot_start)

                session = StudySession(
                    course_name=course_name,
                    assessment_name=assessment.name,
                    topic=topic,
                    session_date=s_date.isoformat(),
                    start_time=slot_start,
                    end_time=slot_end,
                    duration_hours=duration,
                    is_completed=False,
                    is_revision=is_revision,
                    notes=f"Targeting {assessment.name} ({assessment.weight_percentage or 0}%).",
                )
                all_sessions.append(session)

        # Sort all sessions chronologically
        all_sessions.sort(key=lambda s: (s.session_date, s.start_time))
        total_hours = sum(s.duration_hours for s in all_sessions)

        summary = (
            f"Generated {len(all_sessions)} study sessions totaling {total_hours:.1f} hours "
            f"across {len(active_assessments)} assessments."
        )

        return StudyPlan(
            course_id=course_id,
            course_name=course_name,
            total_planned_hours=round(total_hours, 1),
            preferences=preferences,
            sessions=all_sessions,
            warnings=warnings,
            summary=summary,
        )

    def _allocate_time_slot(self, base_start: str, duration_hours: float, index: int) -> Tuple[str, str]:
        """Calculates start and end time offset if multiple sessions occur on the same day."""
        base_h, base_m = map(int, base_start.split(":"))
        offset_minutes = int(index * (duration_hours * 60 + 15))  # 15 min buffer between blocks
        total_start_min = base_h * 60 + base_m + offset_minutes
        
        # Don't exceed 23:45
        if total_start_min > 23 * 60:
            total_start_min = 23 * 60

        start_h = (total_start_min // 60) % 24
        start_m = total_start_min % 60

        total_end_min = total_start_min + int(duration_hours * 60)
        end_h = (total_end_min // 60) % 24
        end_m = total_end_min % 60

        return f"{start_h:02d}:{start_m:02d}", f"{end_h:02d}:{end_m:02d}"
