"""Registered Callable Agent Tools for SyllabusPilotAgent."""
import os
from typing import List, Dict, Any, Optional
from datetime import date

from models.schemas import (
    AssessmentItem,
    CourseMetadata,
    ExtractedSyllabus,
    StudyPreferences,
    StudyPlan,
    ReplanProposal,
    WorkloadSummary,
    PracticeQuestion,
)
from services.extraction import SyllabusExtractor
from services.scheduling import StudyScheduler
from services.priority import WorkloadBalancer
from services.replanning import AdaptiveRecoveryEngine
from services.calendar_export import CalendarExporter
from services.study_coach import StudyCoachService
from repositories.course_repository import CourseRepository
from repositories.study_repository import StudyRepository


class SyllabusPilotTools:
    """Toolkit encapsulating all deterministic services and repository actions."""

    def __init__(self, db_path: Optional[str] = None, api_key: Optional[str] = None):
        self.db_path = db_path
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.extractor = SyllabusExtractor(api_key=self.api_key)
        self.scheduler = StudyScheduler()
        self.balancer = WorkloadBalancer(self.scheduler)
        self.recovery = AdaptiveRecoveryEngine(self.scheduler)
        self.calendar = CalendarExporter()
        self.coach = StudyCoachService(api_key=self.api_key)
        self.course_repo = CourseRepository(db_path)
        self.study_repo = StudyRepository(db_path)

    def extract_syllabus_information(self, text_or_filepath: str) -> Dict[str, Any]:
        """Tool 1: Extracts course metadata, assessments, and deadlines from syllabus text or file path."""
        if os.path.exists(text_or_filepath) and text_or_filepath.lower().endswith(".pdf"):
            extracted = self.extractor.extract_from_pdf(text_or_filepath)
        else:
            extracted = self.extractor.extract_from_text(text_or_filepath)
        
        # Save to database
        course_id = self.course_repo.save_course(extracted.course)
        saved_assessments = self.course_repo.save_assessments(course_id, extracted.assessments)
        
        return {
            "course_id": course_id,
            "course_name": extracted.course.course_name,
            "course_code": extracted.course.course_code,
            "assessments_count": len(saved_assessments),
            "topics_count": len(extracted.course.topics),
            "unparsed_notes": extracted.unparsed_notes,
        }

    def validate_extracted_deadlines(self, course_id: int) -> Dict[str, Any]:
        """Tool 2: Validates extracted assessment dates, missing weights, and review statuses."""
        assessments = self.course_repo.get_assessments(course_id)
        if not assessments:
            return {"status": "error", "message": f"No assessments found for course {course_id}."}

        needs_review = [a for a in assessments if a.verification_status == "Needs Review" or not a.deadline]
        total_weight = sum(a.weight_percentage or 0.0 for a in assessments)

        return {
            "total_assessments": len(assessments),
            "needs_review_count": len(needs_review),
            "needs_review_items": [a.name for a in needs_review],
            "total_grading_weight_sum": round(total_weight, 1),
            "is_valid": len(needs_review) == 0 and abs(total_weight - 100.0) < 1.0,
        }

    def generate_study_plan(
        self,
        course_id: int,
        hours_per_week: float = 10.0,
        available_days: Optional[List[str]] = None,
        preferred_time_of_day: str = "Evening",
        start_date: Optional[str] = None,
        reference_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Tool 3: Generates a deterministic study schedule respecting deadlines and weekly hours."""
        course = self.course_repo.get_course(course_id)
        if not course:
            return {"status": "error", "message": f"Course {course_id} not found."}

        assessments = self.course_repo.get_assessments(course_id)
        prefs = StudyPreferences(
            hours_per_week=hours_per_week,
            available_days=available_days or ["Monday", "Wednesday", "Friday"],
            preferred_time_of_day=preferred_time_of_day,
            start_date=start_date or (course.semester_start if course.semester_start else None),
        )

        plan = self.scheduler.generate_plan(
            course_id=course_id,
            course_name=course.course_name,
            assessments=assessments,
            preferences=prefs,
            reference_date=reference_date,
        )

        plan_id = self.study_repo.save_plan(plan)
        return {
            "plan_id": plan_id,
            "course_name": course.course_name,
            "total_sessions": len(plan.sessions),
            "total_planned_hours": plan.total_planned_hours,
            "warnings": plan.warnings,
            "summary": plan.summary,
        }

    def calculate_workload_priorities(self, course_id: int) -> Dict[str, Any]:
        """Tool 4: Evaluates deadline proximity, effort, and grading percentages to rank assessment priorities."""
        assessments = self.course_repo.get_assessments(course_id)
        plan = self.study_repo.get_active_plan_for_course(course_id)
        sessions = plan.sessions if plan else []

        priorities = self.balancer.calculate_priorities(assessments, sessions)
        summary = self.balancer.analyze_workload(plan, assessments) if plan else None

        return {
            "priorities": [p.model_dump() for p in priorities],
            "overloaded_weeks_count": len(summary.overloaded_weeks) if summary else 0,
            "recommendations": summary.recommendations if summary else [],
        }

    def replan_missed_study_sessions(
        self,
        plan_id: int,
        reason: str = "Missed sessions due to emergency/illness",
        current_date_iso: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Tool 5: Redistributes missed uncompleted study sessions into future available calendar slots."""
        plan = self.study_repo.get_plan(plan_id)
        if not plan:
            return {"status": "error", "message": f"Plan {plan_id} not found."}

        assessments = self.course_repo.get_assessments(plan.course_id)
        ref_date = date.fromisoformat(current_date_iso) if current_date_iso else date.today()

        proposal = self.recovery.propose_recovery(
            current_plan=plan,
            current_date=ref_date,
            reason=reason,
            assessments=assessments,
        )

        # Apply new plan directly when called via agent tool
        self.study_repo.replace_sessions(plan_id, proposal.redistributed_sessions)
        self.study_repo.record_replan_history(
            plan_id=plan_id,
            reason=reason,
            missed_count=len(proposal.missed_sessions),
            redistributed_count=len(proposal.redistributed_sessions),
            explanation=proposal.explanation,
        )

        return {
            "status": "success",
            "missed_count": len(proposal.missed_sessions),
            "preserved_completed_count": len(proposal.completed_sessions),
            "explanation": proposal.explanation,
            "warnings": proposal.warnings,
        }

    def export_calendar_events(self, plan_id: int) -> bytes:
        """Tool 6: Generates RFC 5545 ICS calendar byte content for Google Calendar export."""
        plan = self.study_repo.get_plan(plan_id)
        if not plan:
            raise ValueError(f"Plan {plan_id} not found.")
        assessments = self.course_repo.get_assessments(plan.course_id)
        return self.calendar.export_plan_to_ics(plan, assessments=assessments)

    def track_study_progress(self, plan_id: int, session_id: Optional[int] = None, mark_done: bool = True) -> Dict[str, Any]:
        """Tool 7: Toggles session completion status and returns updated progress metrics."""
        if session_id:
            self.study_repo.update_session_completion(session_id, mark_done)
        
        metrics = self.study_repo.get_progress_metrics(plan_id)
        return {
            "plan_id": plan_id,
            "metrics": metrics,
        }

    def generate_practice_questions(self, course_name: str, topic: str, count: int = 3) -> List[Dict[str, Any]]:
        """Tool 8: Generates topic-specific multiple choice practice questions and explanations."""
        questions = self.coach.generate_practice_questions(course_name, topic, count=count)
        return [q.model_dump() for q in questions]
