"""Pydantic schemas for SyllabusPilot."""
from __future__ import annotations

import uuid
from datetime import datetime, date, time
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


class AssessmentType(str, Enum):
    EXAM = "Exam"
    MIDTERM = "Midterm"
    FINAL = "Final"
    ASSIGNMENT = "Assignment"
    PROJECT = "Project"
    QUIZ = "Quiz"
    LAB = "Lab"
    PRESENTATION = "Presentation"
    OTHER = "Other"

    @classmethod
    def from_string(cls, value: str) -> "AssessmentType":
        if not value:
            return cls.OTHER
        val_lower = value.strip().lower()
        if "final" in val_lower:
            return cls.FINAL
        if "midterm" in val_lower:
            return cls.MIDTERM
        if "exam" in val_lower or "test" in val_lower:
            return cls.EXAM
        if "assign" in val_lower or "homework" in val_lower or "pset" in val_lower:
            return cls.ASSIGNMENT
        if "proj" in val_lower or "capstone" in val_lower:
            return cls.PROJECT
        if "quiz" in val_lower:
            return cls.QUIZ
        if "lab" in val_lower:
            return cls.LAB
        if "present" in val_lower or "defense" in val_lower:
            return cls.PRESENTATION
        return cls.OTHER


class VerificationStatus(str, Enum):
    VERIFIED = "Verified"
    NEEDS_REVIEW = "Needs Review"
    CONFIRMED_BY_USER = "Confirmed by User"


class AssessmentItem(BaseModel):
    id: Optional[int] = None
    course_id: Optional[int] = None
    name: str = Field(..., description="Name of the assessment, e.g. Midterm 1, Assignment 2")
    assessment_type: AssessmentType = Field(default=AssessmentType.OTHER)
    deadline: Optional[str] = Field(None, description="ISO formatted deadline string: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
    weight_percentage: Optional[float] = Field(None, ge=0.0, le=100.0, description="Grading weight percentage (0-100)")
    description: Optional[str] = Field(None, description="Short description or instructions")
    topics: List[str] = Field(default_factory=list, description="Topics or chapters covered")
    source_reference: Optional[str] = Field(None, description="Source page, section or quote in syllabus")
    verification_status: VerificationStatus = Field(default=VerificationStatus.VERIFIED)
    confidence_score: float = Field(default=0.9, ge=0.0, le=1.0)

    @field_validator("weight_percentage", mode="before")
    @classmethod
    def validate_weight(cls, v: Any) -> Optional[float]:
        if v is None or v == "":
            return None
        if isinstance(v, str):
            v_clean = v.replace("%", "").strip()
            try:
                return float(v_clean)
            except ValueError:
                return None
        return float(v)


class CourseMetadata(BaseModel):
    id: Optional[int] = None
    course_name: str = Field(..., description="Official title of the course")
    course_code: Optional[str] = Field(None, description="Course code, e.g. CS101, DS301")
    instructor_name: Optional[str] = Field(None, description="Primary instructor name")
    semester_start: Optional[str] = Field(None, description="Semester start date YYYY-MM-DD")
    semester_end: Optional[str] = Field(None, description="Semester end date YYYY-MM-DD")
    study_hours_recommended_per_week: Optional[float] = Field(None, description="Recommended hours/week if stated")
    raw_syllabus_text: Optional[str] = Field(None, description="Extracted raw text from syllabus document")
    topics: List[str] = Field(default_factory=list, description="Course outline topics or syllabus chapters")


class ExtractedSyllabus(BaseModel):
    course: CourseMetadata
    assessments: List[AssessmentItem] = Field(default_factory=list)
    unparsed_notes: Optional[str] = Field(None, description="Any warnings, missing dates, or policy notes")


class StudyPreferences(BaseModel):
    hours_per_week: float = Field(default=10.0, ge=1.0, le=50.0, description="Target study hours per week")
    available_days: List[str] = Field(
        default=["Monday", "Wednesday", "Friday", "Sunday"],
        description="Available days for study sessions"
    )
    preferred_time_of_day: str = Field(
        default="Evening",
        description="Preferred time block: Morning (09:00), Afternoon (14:00), Evening (18:30), Night (20:30)"
    )
    session_duration_hours: float = Field(default=1.5, ge=0.5, le=4.0, description="Preferred session duration in hours")
    timezone: str = Field(default="Europe/Riga", description="Student's IANA timezone")
    start_date: Optional[str] = Field(None, description="Plan start date YYYY-MM-DD")
    end_date: Optional[str] = Field(None, description="Plan end date YYYY-MM-DD")


class StudySession(BaseModel):
    id: Optional[int] = None
    plan_id: Optional[int] = None
    course_name: str
    assessment_name: str
    topic: str
    session_date: str = Field(..., description="YYYY-MM-DD")
    start_time: str = Field(..., description="HH:MM")
    end_time: str = Field(..., description="HH:MM")
    duration_hours: float
    is_completed: bool = False
    completed_at: Optional[str] = None
    notes: Optional[str] = None
    is_revision: bool = False
    session_uid: str = Field(default_factory=lambda: str(uuid.uuid4()))


class PriorityAssessment(BaseModel):
    assessment_id: Optional[int] = None
    assessment_name: str
    assessment_type: str
    deadline: Optional[str] = None
    weight_percentage: float = 0.0
    days_remaining: Optional[int] = None
    priority_score: float = Field(..., ge=0.0, le=100.0)
    priority_tier: str = Field(..., description="High, Medium, or Low")
    estimated_effort_hours: float = 0.0
    progress_percentage: float = 0.0
    explanation: str


class WorkloadWeek(BaseModel):
    week_start: str
    week_end: str
    planned_hours: float
    available_hours: float
    is_overloaded: bool
    assessments_due: List[str] = Field(default_factory=list)


class WorkloadSummary(BaseModel):
    total_planned_hours: float
    total_available_hours: float
    total_completed_hours: float
    overloaded_weeks: List[WorkloadWeek] = Field(default_factory=list)
    upcoming_critical_deadlines: List[PriorityAssessment] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class StudyPlan(BaseModel):
    id: Optional[int] = None
    course_id: int
    course_name: str
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    total_planned_hours: float = 0.0
    preferences: StudyPreferences
    sessions: List[StudySession] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    summary: str = ""


class ReplanProposal(BaseModel):
    missed_sessions: List[StudySession]
    completed_sessions: List[StudySession]
    redistributed_sessions: List[StudySession]
    unchanged_sessions: List[StudySession]
    net_hours_difference: float
    explanation: str
    warnings: List[str] = Field(default_factory=list)


class PracticeQuestion(BaseModel):
    question: str
    options: List[str] = Field(..., min_length=2, max_length=5)
    correct_answer_index: int = Field(..., ge=0)
    explanation: str
    topic: str
    difficulty: str = "Medium"


class QuizSubmission(BaseModel):
    selected_index: int
    is_correct: bool
    feedback: str
