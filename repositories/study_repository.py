"""Repository for managing Study Plans, Sessions, Completion, and Replanning history."""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from models.database import get_connection
from models.schemas import StudyPlan, StudySession, StudyPreferences


class StudyRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def save_plan(self, plan: StudyPlan) -> int:
        """Inserts a new study plan and returns its ID."""
        conn = get_connection(self.db_path)
        try:
            with conn:
                available_days_json = json.dumps(plan.preferences.available_days)
                cursor = conn.execute(
                    """
                    INSERT INTO study_plans (
                        course_id, course_name, total_planned_hours, hours_per_week,
                        available_days_json, preferred_time_of_day, session_duration_hours,
                        timezone, summary, is_active
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1);
                    """,
                    (
                        plan.course_id,
                        plan.course_name,
                        plan.total_planned_hours,
                        plan.preferences.hours_per_week,
                        available_days_json,
                        plan.preferences.preferred_time_of_day,
                        plan.preferences.session_duration_hours,
                        plan.preferences.timezone,
                        plan.summary,
                    ),
                )
                plan_id = cursor.lastrowid
        finally:
            conn.close()

        # Save associated sessions after plan transaction completes
        if plan.sessions:
            self.save_sessions(plan_id, plan.sessions)
            
        return plan_id

    def get_plan(self, plan_id: int) -> Optional[StudyPlan]:
        """Fetches a study plan and all its sessions by plan_id."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute("SELECT * FROM study_plans WHERE id = ?;", (plan_id,))
            row = cursor.fetchone()
            if not row:
                return None

            available_days = ["Monday", "Wednesday", "Friday"]
            if row["available_days_json"]:
                try:
                    available_days = json.loads(row["available_days_json"])
                except Exception:
                    pass

            prefs = StudyPreferences(
                hours_per_week=row["hours_per_week"],
                available_days=available_days,
                preferred_time_of_day=row["preferred_time_of_day"] or "Evening",
                session_duration_hours=row["session_duration_hours"] or 1.5,
                timezone=row["timezone"] or "Europe/Riga",
            )
        finally:
            conn.close()

        sessions = self.get_sessions_for_plan(plan_id)

        return StudyPlan(
            id=row["id"],
            course_id=row["course_id"],
            course_name=row["course_name"],
            created_at=str(row["created_at"]),
            total_planned_hours=row["total_planned_hours"],
            preferences=prefs,
            sessions=sessions,
            summary=row["summary"] or "",
        )

    def get_active_plan_for_course(self, course_id: int) -> Optional[StudyPlan]:
        """Fetches the latest active study plan for a given course."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                "SELECT id FROM study_plans WHERE course_id = ? AND is_active = 1 ORDER BY id DESC LIMIT 1;",
                (course_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            plan_id = row["id"]
        finally:
            conn.close()

        return self.get_plan(plan_id)

    def save_sessions(self, plan_id: int, sessions: List[StudySession]) -> List[StudySession]:
        """Saves a batch of study sessions for a plan."""
        conn = get_connection(self.db_path)
        try:
            with conn:
                saved = []
                for s in sessions:
                    cursor = conn.execute(
                        """
                        INSERT INTO study_sessions (
                            plan_id, session_uid, course_name, assessment_name,
                            topic, session_date, start_time, end_time,
                            duration_hours, is_completed, completed_at, notes, is_revision
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                        """,
                        (
                            plan_id,
                            s.session_uid,
                            s.course_name,
                            s.assessment_name,
                            s.topic,
                            s.session_date,
                            s.start_time,
                            s.end_time,
                            s.duration_hours,
                            1 if s.is_completed else 0,
                            s.completed_at,
                            s.notes,
                            1 if s.is_revision else 0,
                        ),
                    )
                    sc = s.model_copy()
                    sc.id = cursor.lastrowid
                    sc.plan_id = plan_id
                    saved.append(sc)
                return saved
        finally:
            conn.close()

    def get_sessions_for_plan(self, plan_id: int) -> List[StudySession]:
        """Gets all sessions belonging to a plan ordered chronologically."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT * FROM study_sessions
                WHERE plan_id = ?
                ORDER BY session_date ASC, start_time ASC;
                """,
                (plan_id,),
            )
            sessions = []
            for r in cursor.fetchall():
                sessions.append(
                    StudySession(
                        id=r["id"],
                        plan_id=r["plan_id"],
                        session_uid=r["session_uid"],
                        course_name=r["course_name"],
                        assessment_name=r["assessment_name"],
                        topic=r["topic"],
                        session_date=r["session_date"],
                        start_time=r["start_time"],
                        end_time=r["end_time"],
                        duration_hours=r["duration_hours"],
                        is_completed=bool(r["is_completed"]),
                        completed_at=r["completed_at"],
                        notes=r["notes"],
                        is_revision=bool(r["is_revision"]),
                    )
                )
            return sessions
        finally:
            conn.close()

    def update_session_completion(
        self, session_id: int, is_completed: bool, notes: Optional[str] = None
    ) -> bool:
        """Toggles session completion and logs timestamp."""
        conn = get_connection(self.db_path)
        try:
            completed_at = datetime.utcnow().isoformat() if is_completed else None
            with conn:
                cursor = conn.execute(
                    """
                    UPDATE study_sessions
                    SET is_completed = ?, completed_at = ?, notes = COALESCE(?, notes)
                    WHERE id = ?;
                    """,
                    (1 if is_completed else 0, completed_at, notes, session_id),
                )
                action_name = "COMPLETED" if is_completed else "UNCOMPLETED"
                conn.execute(
                    """
                    INSERT INTO progress_logs (session_id, action, details)
                    VALUES (?, ?, ?);
                    """,
                    (session_id, action_name, f"Notes: {notes or 'None'}"),
                )
                return cursor.rowcount > 0
        finally:
            conn.close()

    def replace_sessions(self, plan_id: int, new_sessions: List[StudySession]) -> None:
        """Replaces all sessions of a plan (used during replanning confirmation)."""
        conn = get_connection(self.db_path)
        try:
            with conn:
                conn.execute("DELETE FROM study_sessions WHERE plan_id = ?;", (plan_id,))
                total_hours = sum(s.duration_hours for s in new_sessions)
                conn.execute(
                    "UPDATE study_plans SET total_planned_hours = ? WHERE id = ?;",
                    (total_hours, plan_id),
                )
        finally:
            conn.close()

        self.save_sessions(plan_id, new_sessions)

    def record_replan_history(
        self, plan_id: int, reason: str, missed_count: int, redistributed_count: int, explanation: str
    ) -> int:
        """Saves a replanning log entry."""
        conn = get_connection(self.db_path)
        try:
            with conn:
                cursor = conn.execute(
                    """
                    INSERT INTO replan_history (
                        plan_id, reason, missed_sessions_count, redistributed_sessions_count, explanation
                    ) VALUES (?, ?, ?, ?, ?);
                    """,
                    (plan_id, reason, missed_count, redistributed_count, explanation),
                )
                return cursor.lastrowid
        finally:
            conn.close()

    def get_progress_metrics(self, plan_id: int) -> Dict[str, Any]:
        """Calculates completed hours, remaining hours, and progress % for a plan."""
        conn = get_connection(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total_sessions,
                    SUM(duration_hours) as total_hours,
                    SUM(CASE WHEN is_completed = 1 THEN 1 ELSE 0 END) as completed_sessions,
                    SUM(CASE WHEN is_completed = 1 THEN duration_hours ELSE 0 END) as completed_hours
                FROM study_sessions
                WHERE plan_id = ?;
                """,
                (plan_id,),
            )
            row = cursor.fetchone()
            if not row or not row["total_sessions"]:
                return {
                    "total_sessions": 0,
                    "total_hours": 0.0,
                    "completed_sessions": 0,
                    "completed_hours": 0.0,
                    "remaining_hours": 0.0,
                    "progress_percentage": 0.0,
                }

            total_sessions = row["total_sessions"] or 0
            total_hours = row["total_hours"] or 0.0
            completed_sessions = row["completed_sessions"] or 0
            completed_hours = row["completed_hours"] or 0.0
            remaining_hours = max(0.0, total_hours - completed_hours)
            progress_pct = (completed_hours / total_hours * 100.0) if total_hours > 0 else 0.0

            return {
                "total_sessions": total_sessions,
                "total_hours": round(total_hours, 1),
                "completed_sessions": completed_sessions,
                "completed_hours": round(completed_hours, 1),
                "remaining_hours": round(remaining_hours, 1),
                "progress_percentage": round(progress_pct, 1),
            }
        finally:
            conn.close()
