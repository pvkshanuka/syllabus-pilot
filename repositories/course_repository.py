"""Repository for managing Courses, Syllabi metadata, and Assessments."""
import json
from typing import List, Optional
from models.database import get_connection
from models.schemas import CourseMetadata, AssessmentItem, AssessmentType, VerificationStatus


class CourseRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def save_course(self, course: CourseMetadata) -> int:
        """Inserts or updates a course and returns the course_id."""
        conn = get_connection(self.db_path)
        try:
            with conn:
                topics_json = json.dumps(course.topics or [])
                if course.id:
                    conn.execute(
                        """
                        UPDATE courses
                        SET course_name = ?, course_code = ?, instructor_name = ?,
                            semester_start = ?, semester_end = ?, study_hours_recommended_per_week = ?,
                            raw_syllabus_text = ?, topics_json = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?;
                        """,
                        (
                            course.course_name,
                            course.course_code,
                            course.instructor_name,
                            course.semester_start,
                            course.semester_end,
                            course.study_hours_recommended_per_week,
                            course.raw_syllabus_text,
                            topics_json,
                            course.id,
                        ),
                    )
                    return course.id
                else:
                    cursor = conn.execute(
                        """
                        INSERT INTO courses (
                            course_name, course_code, instructor_name, semester_start,
                            semester_end, study_hours_recommended_per_week, raw_syllabus_text, topics_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            course.course_name,
                            course.course_code,
                            course.instructor_name,
                            course.semester_start,
                            course.semester_end,
                            course.study_hours_recommended_per_week,
                            course.raw_syllabus_text,
                            topics_json,
                        ),
                    )
                    return cursor.lastrowid
        finally:
            conn.close()

    def get_course(self, course_id: int) -> Optional[CourseMetadata]:
        """Fetches a course by ID."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("SELECT * FROM courses WHERE id = ?;", (course_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            topics = []
            if row["topics_json"]:
                try:
                    topics = json.loads(row["topics_json"])
                except Exception:
                    topics = []

            return CourseMetadata(
                id=row["id"],
                course_name=row["course_name"],
                course_code=row["course_code"],
                instructor_name=row["instructor_name"],
                semester_start=row["semester_start"],
                semester_end=row["semester_end"],
                study_hours_recommended_per_week=row["study_hours_recommended_per_week"],
                raw_syllabus_text=row["raw_syllabus_text"],
                topics=topics,
            )
        finally:
            conn.close()

    def list_courses(self) -> List[CourseMetadata]:
        """Lists all registered courses."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("SELECT * FROM courses ORDER BY id DESC;")
            courses = []
            for row in cursor.fetchall():
                topics = []
                if row["topics_json"]:
                    try:
                        topics = json.loads(row["topics_json"])
                    except Exception:
                        topics = []
                courses.append(
                    CourseMetadata(
                        id=row["id"],
                        course_name=row["course_name"],
                        course_code=row["course_code"],
                        instructor_name=row["instructor_name"],
                        semester_start=row["semester_start"],
                        semester_end=row["semester_end"],
                        study_hours_recommended_per_week=row["study_hours_recommended_per_week"],
                        raw_syllabus_text=row["raw_syllabus_text"],
                        topics=topics,
                    )
                )
            return courses
        finally:
            conn.close()

    def delete_course(self, course_id: int) -> bool:
        """Deletes a course and all related assessments and plans (via CASCADE)."""
        conn = get_connection(self.db_path)
        try:
            with conn:
                cursor = conn.execute("DELETE FROM courses WHERE id = ?;", (course_id,))
                return cursor.rowcount > 0
        finally:
            conn.close()

    def save_assessments(self, course_id: int, assessments: List[AssessmentItem]) -> List[AssessmentItem]:
        """Replaces assessments for a given course or inserts new ones."""
        conn = get_connection(self.db_path)
        try:
            with conn:
                conn.execute("DELETE FROM assessments WHERE course_id = ?;", (course_id,))
                saved_list = []
                for item in assessments:
                    topics_json = json.dumps(item.topics or [])
                    cursor = conn.execute(
                        """
                        INSERT INTO assessments (
                            course_id, name, assessment_type, deadline, weight_percentage,
                            description, topics_json, source_reference, verification_status, confidence_score
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            course_id,
                            item.name,
                            item.assessment_type.value if hasattr(item.assessment_type, 'value') else str(item.assessment_type),
                            item.deadline,
                            item.weight_percentage,
                            item.description,
                            topics_json,
                            item.source_reference,
                            item.verification_status.value if hasattr(item.verification_status, 'value') else str(item.verification_status),
                            item.confidence_score,
                        ),
                    )
                    item_copy = item.model_copy()
                    item_copy.id = cursor.lastrowid
                    item_copy.course_id = course_id
                    saved_list.append(item_copy)
                return saved_list
        finally:
            conn.close()

    def get_assessments(self, course_id: int) -> List[AssessmentItem]:
        """Fetches all assessments for a course ordered by deadline."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT * FROM assessments WHERE course_id = ? ORDER BY deadline ASC, id ASC;",
                (course_id,),
            )
            items = []
            for row in cursor.fetchall():
                topics = []
                if row["topics_json"]:
                    try:
                        topics = json.loads(row["topics_json"])
                    except Exception:
                        topics = []
                
                try:
                    a_type = AssessmentType(row["assessment_type"])
                except Exception:
                    a_type = AssessmentType.from_string(row["assessment_type"])

                try:
                    v_status = VerificationStatus(row["verification_status"])
                except Exception:
                    v_status = VerificationStatus.VERIFIED

                items.append(
                    AssessmentItem(
                        id=row["id"],
                        course_id=row["course_id"],
                        name=row["name"],
                        assessment_type=a_type,
                        deadline=row["deadline"],
                        weight_percentage=row["weight_percentage"],
                        description=row["description"],
                        topics=topics,
                        source_reference=row["source_reference"],
                        verification_status=v_status,
                        confidence_score=row["confidence_score"] or 0.9,
                    )
                )
            return items
        finally:
            conn.close()

    def update_assessment(self, item: AssessmentItem) -> bool:
        """Updates a single assessment item."""
        if not item.id:
            return False
        conn = get_connection(self.db_path)
        try:
            with conn:
                topics_json = json.dumps(item.topics or [])
                cursor = conn.execute(
                    """
                    UPDATE assessments
                    SET name = ?, assessment_type = ?, deadline = ?, weight_percentage = ?,
                        description = ?, topics_json = ?, source_reference = ?,
                        verification_status = ?, confidence_score = ?
                    WHERE id = ?;
                    """,
                    (
                        item.name,
                        item.assessment_type.value if hasattr(item.assessment_type, 'value') else str(item.assessment_type),
                        item.deadline,
                        item.weight_percentage,
                        item.description,
                        topics_json,
                        item.source_reference,
                        item.verification_status.value if hasattr(item.verification_status, 'value') else str(item.verification_status),
                        item.confidence_score,
                        item.id,
                    ),
                )
                return cursor.rowcount > 0
        finally:
            conn.close()

    def delete_assessment(self, assessment_id: int) -> bool:
        """Deletes an assessment item."""
        conn = get_connection(self.db_path)
        try:
            with conn:
                cursor = conn.execute("DELETE FROM assessments WHERE id = ?;", (assessment_id,))
                return cursor.rowcount > 0
        finally:
            conn.close()
