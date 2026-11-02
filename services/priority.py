"""Smart Priority & Workload Balancer: Multi-factor scoring and weekly capacity analysis."""
from datetime import date, datetime, timedelta
from typing import List, Optional, Dict
from models.schemas import (
    AssessmentItem,
    AssessmentType,
    PriorityAssessment,
    StudyPlan,
    StudySession,
    WorkloadSummary,
    WorkloadWeek,
)
from services.scheduling import StudyScheduler


class WorkloadBalancer:
    """Calculates multi-factor priority scores and detects overloaded weeks with proactive balancing."""

    def __init__(self, scheduler: Optional[StudyScheduler] = None):
        self.scheduler = scheduler or StudyScheduler()

    def calculate_priorities(
        self,
        assessments: List[AssessmentItem],
        sessions: Optional[List[StudySession]] = None,
        reference_date: Optional[date] = None,
    ) -> List[PriorityAssessment]:
        """Calculates transparent multi-factor priority scores for assessments."""
        today = reference_date or date.today()
        sessions = sessions or []

        results: List[PriorityAssessment] = []

        # Map session progress by assessment name
        progress_map: Dict[str, Dict[str, float]] = {}
        for s in sessions:
            stat = progress_map.setdefault(s.assessment_name, {"total": 0.0, "done": 0.0})
            stat["total"] += s.duration_hours
            if s.is_completed:
                stat["done"] += s.duration_hours

        for a in assessments:
            weight = a.weight_percentage if a.weight_percentage is not None else 10.0
            effort_hours = self.scheduler.estimate_effort_hours(a)

            # Days remaining
            days_rem: Optional[int] = None
            if a.deadline:
                try:
                    d_date = datetime.strptime(a.deadline[:10], "%Y-%m-%d").date()
                    days_rem = (d_date - today).days
                except ValueError:
                    pass

            # 1. Proximity score (0 to 40 pts)
            if days_rem is None:
                proximity_score = 10.0
            elif days_rem <= 0:
                proximity_score = 40.0
            elif days_rem <= 7:
                proximity_score = 40.0 - (days_rem * 1.5)
            elif days_rem <= 30:
                proximity_score = 25.0 - ((days_rem - 7) * 0.7)
            else:
                proximity_score = max(5.0, 10.0 - ((days_rem - 30) * 0.1))

            # 2. Weight score (0 to 35 pts)
            weight_score = min(35.0, weight * 0.9)

            # 3. Effort score (0 to 15 pts)
            effort_score = min(15.0, effort_hours * 0.75)

            # 4. Incompletion score (0 to 10 pts)
            prog = progress_map.get(a.name, {"total": 0.0, "done": 0.0})
            total_h = prog["total"]
            done_h = prog["done"]
            prog_pct = (done_h / total_h * 100.0) if total_h > 0 else 0.0
            incompletion_score = (1.0 - (prog_pct / 100.0)) * 10.0

            total_score = round(proximity_score + weight_score + effort_score + incompletion_score, 1)
            total_score = min(100.0, max(0.0, total_score))

            # Tier classification
            if total_score >= 70.0:
                tier = "High"
            elif total_score >= 40.0:
                tier = "Medium"
            else:
                tier = "Low"

            # Explanation
            due_str = f"due in {days_rem} days" if days_rem is not None else "no set deadline"
            explanation = (
                f"{tier} Priority ({total_score}/100): {due_str}, {weight}% weight, "
                f"{effort_hours}h estimated effort ({prog_pct:.0f}% completed)."
            )

            results.append(
                PriorityAssessment(
                    assessment_id=a.id,
                    assessment_name=a.name,
                    assessment_type=a.assessment_type.value if hasattr(a.assessment_type, 'value') else a.assessment_type,
                    deadline=a.deadline,
                    weight_percentage=weight,
                    days_remaining=days_rem,
                    priority_score=total_score,
                    priority_tier=tier,
                    estimated_effort_hours=effort_hours,
                    progress_percentage=round(prog_pct, 1),
                    explanation=explanation,
                )
            )

        # Sort highest priority first
        results.sort(key=lambda x: x.priority_score, reverse=True)
        return results

    def analyze_workload(
        self,
        plan: StudyPlan,
        assessments: Optional[List[AssessmentItem]] = None,
        reference_date: Optional[date] = None,
    ) -> WorkloadSummary:
        """Analyzes week-by-week study workload and detects overloads."""
        today = reference_date or date.today()
        sessions = plan.sessions
        available_per_week = plan.preferences.hours_per_week

        # Group sessions by calendar week (Monday to Sunday)
        weeks_map: Dict[str, Dict] = {}
        for s in sessions:
            s_date = datetime.strptime(s.session_date, "%Y-%m-%d").date()
            monday = s_date - timedelta(days=s_date.weekday())
            sunday = monday + timedelta(days=6)
            week_key = monday.isoformat()

            if week_key not in weeks_map:
                weeks_map[week_key] = {
                    "start": monday.isoformat(),
                    "end": sunday.isoformat(),
                    "planned_hours": 0.0,
                    "assessments": set(),
                }
            weeks_map[week_key]["planned_hours"] += s.duration_hours
            weeks_map[week_key]["assessments"].add(s.assessment_name)

        overloaded_weeks: List[WorkloadWeek] = []
        recommendations: List[str] = []

        for wk_key in sorted(weeks_map.keys()):
            data = weeks_map[wk_key]
            planned = round(data["planned_hours"], 1)
            is_overloaded = planned > available_per_week

            week_obj = WorkloadWeek(
                week_start=data["start"],
                week_end=data["end"],
                planned_hours=planned,
                available_hours=available_per_week,
                is_overloaded=is_overloaded,
                assessments_due=list(data["assessments"]),
            )

            if is_overloaded:
                overloaded_weeks.append(week_obj)
                excess = round(planned - available_per_week, 1)
                recommendations.append(
                    f"Week {data['start']} to {data['end']} exceeds available study capacity by "
                    f"{excess} hours ({planned}h planned vs {available_per_week}h available). "
                    f"Consider moving preparation for {', '.join(data['assessments'])} 1-2 weeks earlier."
                )

        priorities = self.calculate_priorities(assessments or [], sessions, reference_date=today)
        critical_deadlines = [p for p in priorities if p.priority_tier == "High"]

        total_planned = sum(s.duration_hours for s in sessions)
        total_completed = sum(s.duration_hours for s in sessions if s.is_completed)

        return WorkloadSummary(
            total_planned_hours=round(total_planned, 1),
            total_available_hours=round(available_per_week * max(1, len(weeks_map)), 1),
            total_completed_hours=round(total_completed, 1),
            overloaded_weeks=overloaded_weeks,
            upcoming_critical_deadlines=critical_deadlines,
            recommendations=recommendations,
        )
