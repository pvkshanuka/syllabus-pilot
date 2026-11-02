"""Adaptive Study Recovery Engine: Replanning missed sessions with before/after comparison."""
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple, Dict
from models.schemas import (
    StudyPlan,
    StudySession,
    ReplanProposal,
    AssessmentItem,
)
from services.scheduling import StudyScheduler


class AdaptiveRecoveryEngine:
    """Detects missed study sessions and redistributes unfinished workload into future slots."""

    def __init__(self, scheduler: Optional[StudyScheduler] = None):
        self.scheduler = scheduler or StudyScheduler()

    def propose_recovery(
        self,
        current_plan: StudyPlan,
        current_date: Optional[date] = None,
        missed_dates: Optional[List[str]] = None,
        reason: str = "Missed study sessions",
        assessments: Optional[List[AssessmentItem]] = None,
    ) -> ReplanProposal:
        """Calculates a replan proposal preserving completed sessions and moving missed sessions."""
        today = current_date or date.today()
        missed_set = set(missed_dates) if missed_dates else set()

        completed: List[StudySession] = []
        missed: List[StudySession] = []
        future_uncompleted: List[StudySession] = []

        for s in current_plan.sessions:
            if s.is_completed:
                completed.append(s)
            else:
                s_date = datetime.strptime(s.session_date, "%Y-%m-%d").date()
                if s.session_date in missed_set or s_date < today:
                    missed.append(s)
                else:
                    future_uncompleted.append(s)

        if not missed:
            return ReplanProposal(
                missed_sessions=[],
                completed_sessions=completed,
                redistributed_sessions=current_plan.sessions,
                unchanged_sessions=current_plan.sessions,
                net_hours_difference=0.0,
                explanation="No missed sessions found to redistribute. Schedule is currently on track!",
                warnings=[],
            )

        # Build deadline lookup
        deadline_map: Dict[str, date] = {}
        if assessments:
            for a in assessments:
                if a.deadline:
                    try:
                        deadline_map[a.name] = datetime.strptime(a.deadline[:10], "%Y-%m-%d").date()
                    except ValueError:
                        pass

        # Build candidate slots from today onwards based on preferences
        pref_days_indices = {
            self.scheduler.DAY_NAME_TO_INT[d]
            for d in current_plan.preferences.available_days
            if d in self.scheduler.DAY_NAME_TO_INT
        } or {0, 2, 4}

        # Available calendar slots from today up to 90 days out
        available_dates: List[date] = []
        curr = today
        for _ in range(120):
            if curr.weekday() in pref_days_indices:
                available_dates.append(curr)
            curr += timedelta(days=1)

        # Group unfinished tasks
        unfinished_tasks = missed + future_uncompleted
        # Sort tasks by assessment deadline urgency
        def get_task_urgency(sess: StudySession) -> date:
            if sess.assessment_name in deadline_map:
                return deadline_map[sess.assessment_name]
            return today + timedelta(days=60)

        unfinished_tasks.sort(key=get_task_urgency)

        redistributed: List[StudySession] = []
        occupied_slots: Dict[date, List[str]] = {}
        warnings: List[str] = []

        start_t_str, _ = self.scheduler.TIME_BLOCK_MAPPINGS.get(
            current_plan.preferences.preferred_time_of_day, ("18:30", "20:00")
        )
        duration = current_plan.preferences.session_duration_hours

        for task in unfinished_tasks:
            limit_deadline = deadline_map.get(task.assessment_name)
            
            # Find earliest available date with capacity
            assigned_date = None
            for cand_date in available_dates:
                if limit_deadline and cand_date >= limit_deadline:
                    continue
                times_on_date = occupied_slots.get(cand_date, [])
                # Max 2 sessions per day to prevent overload
                if len(times_on_date) < 2:
                    assigned_date = cand_date
                    break

            if not assigned_date:
                warnings.append(
                    f"Could not fit recovery session for '{task.assessment_name}: {task.topic}' before deadline! "
                    f"Consider adding available study days or increasing hours/week."
                )
                # Assign to earliest available anyway with warning
                assigned_date = available_dates[0]

            times_on_date = occupied_slots.setdefault(assigned_date, [])
            slot_start, slot_end = self.scheduler._allocate_time_slot(
                start_t_str, duration, len(times_on_date)
            )
            times_on_date.append(slot_start)

            new_session = StudySession(
                course_name=task.course_name,
                assessment_name=task.assessment_name,
                topic=task.topic,
                session_date=assigned_date.isoformat(),
                start_time=slot_start,
                end_time=slot_end,
                duration_hours=task.duration_hours,
                is_completed=False,
                is_revision=task.is_revision,
                notes=f"Rescheduled via Adaptive Recovery ({reason}).",
            )
            redistributed.append(new_session)

        # Merge completed sessions and new rescheduled sessions
        all_new = completed + redistributed
        all_new.sort(key=lambda s: (s.session_date, s.start_time))

        old_hours = current_plan.total_planned_hours
        new_hours = sum(s.duration_hours for s in all_new)

        explanation = (
            f"Successfully recovered {len(missed)} missed study session(s) totaling "
            f"{sum(s.duration_hours for s in missed):.1f} hours due to '{reason}'. "
            f"All {len(completed)} completed session(s) were preserved intact. "
            f"Redistributed remaining work across upcoming available days."
        )

        return ReplanProposal(
            missed_sessions=missed,
            completed_sessions=completed,
            redistributed_sessions=all_new,
            unchanged_sessions=completed,
            net_hours_difference=round(new_hours - old_hours, 1),
            explanation=explanation,
            warnings=warnings,
        )
