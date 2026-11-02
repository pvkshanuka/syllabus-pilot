"""SyllabusPilotAgent: Autonomous academic assistant coordinating tools and guidance."""
import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from agent.prompts import STUDY_AGENT_SYSTEM_PROMPT
from agent.tools import SyllabusPilotTools
from models.schemas import StudyPlan, StudySession
from services.extraction import get_gemini_model_candidates

load_dotenv()


class SyllabusPilotAgent:
    """Google ADK agent orchestrating syllabus parsing, study scheduling, recovery, and coaching."""

    def __init__(self, db_path: Optional[str] = None, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
        self.tools = SyllabusPilotTools(db_path=db_path, api_key=self.api_key)
        self.chat_history: List[Dict[str, str]] = []

    @property
    def active_model(self) -> str:
        return os.getenv("GEMINI_MODEL") or self.model_name or "gemini-3.8-flash"

    def _get_genai_client(self):
        if not self.api_key:
            return None
        from google import genai
        return genai.Client(api_key=self.api_key)

    def handle_message(self, user_message: str, context: Optional[Dict[str, Any]] = None) -> str:
        """Processes a student request, invokes relevant tools, and formulates response."""
        context = context or {}
        course_id = context.get("course_id")
        plan_id = context.get("plan_id")
        
        # 1. Check for deterministic tool triggers
        msg_lower = user_message.lower()

        # A: Replanning Trigger
        if any(w in msg_lower for w in ["sick", "missed", "fell behind", "replan", "adjust schedule"]):
            if plan_id:
                res = self.tools.replan_missed_study_sessions(
                    plan_id=plan_id,
                    reason=user_message,
                )
                return (
                    f"**Adaptive Recovery Executed** 🔄\n\n"
                    f"{res['explanation']}\n\n"
                    f"- **Missed Sessions Recovered**: {res['missed_count']}\n"
                    f"- **Preserved Completed Sessions**: {res['preserved_completed_count']}\n\n"
                    f"Your weekly calendar has been updated to keep you on track!"
                )
            else:
                return "I'd be glad to help you adjust your schedule! Please first generate or select an active study plan for your course."

        # B: Priorities Trigger
        if any(w in msg_lower for w in ["priority", "priorities", "workload", "what should i focus"]):
            if course_id:
                res = self.tools.calculate_workload_priorities(course_id)
                top = res["priorities"][:3]
                lines = ["**Your Current Study Priorities** 🎯\n"]
                for p in top:
                    tier_icon = "🔴" if p["priority_tier"] == "High" else "🟡" if p["priority_tier"] == "Medium" else "🟢"
                    lines.append(f"{tier_icon} **{p['assessment_name']}** ({p['priority_tier']} Priority - {p['priority_score']}/100)")
                    lines.append(f"   {p['explanation']}")
                if res["recommendations"]:
                    lines.append("\n**Workload Advice**:")
                    for r in res["recommendations"]:
                        lines.append(f"- {r}")
                return "\n".join(lines)

        # C: Next Session Trigger
        if any(w in msg_lower for w in ["what to study next", "study next", "next session", "next task", "what's next"]):
            if plan_id:
                plan = self.tools.study_repo.get_plan(plan_id)
                if plan:
                    nxt = self.tools.coach.suggest_next_session(plan)
                    if nxt:
                        tip = self.tools.coach.generate_revision_recommendation(
                            course_name=nxt.course_name,
                            topic=nxt.topic,
                            assessment_name=nxt.assessment_name,
                        )
                        return (
                            f"**Next Recommended Study Session** 📖\n\n"
                            f"- **Date & Time**: {nxt.session_date} at {nxt.start_time} - {nxt.end_time} ({nxt.duration_hours}h)\n"
                            f"- **Course**: {nxt.course_name}\n"
                            f"- **Target**: {nxt.assessment_name}\n"
                            f"- **Topic**: {nxt.topic}\n\n"
                            f"**Coach Strategy**:\n{tip}"
                        )
                return "You have completed all scheduled study sessions! Outstanding work!"

        # 2. If Gemini API client is available, leverage LLM for general academic advice
        client = self._get_genai_client()
        if client:
            try:
                from google.genai import types
                course_info = ""
                if course_id:
                    course = self.tools.course_repo.get_course(course_id)
                    if course:
                        course_info = f"Student is enrolled in {course.course_name} ({course.course_code}). Topics: {', '.join(course.topics[:5])}."

                prompt = (
                    f"{course_info}\n"
                    f"Student: {user_message}\n"
                    "Provide a supportive, concise academic response adhering to your system instructions."
                )
                candidate_models = get_gemini_model_candidates(client, self.active_model)
                for model_to_try in candidate_models:
                    try:
                        response = client.models.generate_content(
                            model=model_to_try,
                            contents=[prompt],
                            config=types.GenerateContentConfig(
                                system_instruction=STUDY_AGENT_SYSTEM_PROMPT,
                                temperature=0.4,
                            ),
                        )
                        if response.text:
                            return response.text.strip()
                    except Exception:
                        continue
            except Exception as e:
                pass

        # 3. Fallback friendly response
        return (
            "I am **SyllabusPilotAgent**, your autonomous study partner! 🎓\n\n"
            "Here is how I can assist you right now:\n"
            "- Upload or paste a syllabus in the **Upload Syllabus** tab to automatically extract deadlines.\n"
            "- Answer the 3 personalization questions in **Study Planner** to generate a balanced schedule.\n"
            "- Ask me to *replan* whenever you miss sessions or fall sick.\n"
            "- Generate topic quizzes and study tips in the **AI Study Coach** tab."
        )
