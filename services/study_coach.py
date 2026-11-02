"""AI Study Coach & Pedagogical Assistant for SyllabusPilot."""
import json
import os
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

from models.schemas import (
    StudyPlan,
    StudySession,
    PracticeQuestion,
    AssessmentItem,
)
from agent.prompts import STUDY_COACH_SYSTEM_PROMPT
from services.extraction import get_gemini_model_candidates

load_dotenv()


class StudyCoachService:
    """Provides personalized AI study recommendations, progress analysis, and practice quizzes."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY", "")
        self.model_name = model_name or os.getenv("GEMINI_MODEL", "gemini-3.8-flash")

    @property
    def active_model(self) -> str:
        return os.getenv("GEMINI_MODEL") or self.model_name or "gemini-3.8-flash"

    def _get_genai_client(self):
        """Initializes GenAI client if API key is present."""
        if not self.api_key:
            return None
        from google import genai
        return genai.Client(api_key=self.api_key)

    def suggest_next_session(
        self, plan: StudyPlan, reference_date: Optional[date] = None
    ) -> Optional[StudySession]:
        """Finds the most urgent upcoming uncompleted study session."""
        today = reference_date or date.today()
        uncompleted = [s for s in plan.sessions if not s.is_completed]
        if not uncompleted:
            return None

        # Filter sessions on or after today
        future_or_today = []
        for s in uncompleted:
            try:
                s_date = datetime.strptime(s.session_date, "%Y-%m-%d").date()
                if s_date >= today:
                    future_or_today.append((s_date, s))
            except ValueError:
                pass

        if future_or_today:
            future_or_today.sort(key=lambda x: (x[0], x[1].start_time))
            return future_or_today[0][1]

        # If all uncompleted sessions are in the past (overdue), return the earliest overdue
        uncompleted.sort(key=lambda s: (s.session_date, s.start_time))
        return uncompleted[0]

    def generate_revision_recommendation(
        self, course_name: str, topic: str, assessment_name: str, days_left: Optional[int] = None
    ) -> str:
        """Provides concise, high-impact study strategy advice."""
        client = self._get_genai_client()
        if client:
            try:
                from google.genai import types
                prompt = (
                    f"Student is preparing for '{assessment_name}' in course '{course_name}'. "
                    f"Current topic: '{topic}'. Days until deadline: {days_left if days_left is not None else 'Unknown'}. "
                    "Provide a short, motivating 2-sentence actionable study tip focusing on active recall, "
                    "problem solving, or memory retrieval techniques."
                )
                candidate_models = get_gemini_model_candidates(client, self.active_model)
                for model_to_try in candidate_models:
                    try:
                        response = client.models.generate_content(
                            model=model_to_try,
                            contents=[prompt],
                            config=types.GenerateContentConfig(
                                system_instruction=STUDY_COACH_SYSTEM_PROMPT,
                                temperature=0.7,
                            ),
                        )
                        if response.text:
                            return response.text.strip()
                    except Exception:
                        continue
            except Exception:
                pass

        # Pedagogical deterministic advice fallback
        if days_left is not None and days_left <= 3:
            return (
                f"🚨 Urgent review: Solve timed practice questions on '{topic}' without checking solutions first. "
                f"Review mistakes immediately to solidify retrieval pathways before {assessment_name}."
            )
        return (
            f"💡 Active Recall Tip: Close your notes and summarize the core principles of '{topic}' "
            f"out loud or on a blank sheet (Feynman Technique). Then implement 2 practical exercises targeting {assessment_name}."
        )

    def generate_practice_questions(
        self, course_name: str, topic: str, count: int = 3
    ) -> List[PracticeQuestion]:
        """Generates multiple-choice practice questions tied directly to course topics."""
        client = self._get_genai_client()
        if client:
            try:
                return self._generate_questions_with_gemini(client, course_name, topic, count)
            except Exception:
                pass

        return self._generate_fallback_questions(course_name, topic, count)

    def _generate_questions_with_gemini(
        self, client, course_name: str, topic: str, count: int
    ) -> List[PracticeQuestion]:
        """Calls Gemini API with structured JSON output for quiz generation with multi-model fallback."""
        from google.genai import types

        prompt = f"""
Generate {count} multiple-choice practice questions for a university course '{course_name}' on the topic: '{topic}'.
Return a JSON array of objects conforming to:
[
  {{
    "question": "Clear, rigorous academic question stem",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_answer_index": 0,
    "explanation": "Detailed explanation of why the correct option is right and others are incorrect.",
    "topic": "{topic}",
    "difficulty": "Medium"
  }}
]
"""
        response_text = None
        candidate_models = get_gemini_model_candidates(client, self.active_model)
        for model_to_try in candidate_models:
            try:
                response = client.models.generate_content(
                    model=model_to_try,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        system_instruction=STUDY_COACH_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.3,
                    ),
                )
                if response.text:
                    response_text = response.text
                    break
            except Exception:
                continue

        if not response_text:
            return self._generate_fallback_questions(course_name, topic, count)

        clean_json = response_text.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.startswith("```"):
            clean_json = clean_json[3:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()

        data = json.loads(clean_json)
        questions = []
        for item in data:
            questions.append(
                PracticeQuestion(
                    question=item["question"],
                    options=item["options"],
                    correct_answer_index=int(item["correct_answer_index"]),
                    explanation=item["explanation"],
                    topic=topic,
                    difficulty=item.get("difficulty", "Medium"),
                )
            )
        return questions

    def _generate_fallback_questions(
        self, course_name: str, topic: str, count: int
    ) -> List[PracticeQuestion]:
        """Curated high-yield practice questions for testing or offline usage."""
        topic_lower = topic.lower()

        if "tree" in topic_lower or "graph" in topic_lower:
            return [
                PracticeQuestion(
                    question=f"In the context of '{topic}', what is the average time complexity for searching a balanced Binary Search Tree (BST) with N nodes?",
                    options=["O(1)", "O(log N)", "O(N)", "O(N log N)"],
                    correct_answer_index=1,
                    explanation="In a balanced BST (such as an AVL or Red-Black tree), the height is bounded by O(log N), allowing binary search in logarithmic time.",
                    topic=topic,
                    difficulty="Medium",
                ),
                PracticeQuestion(
                    question=f"Which tree traversal method visits nodes in strictly ascending numerical order for a valid BST?",
                    options=["Pre-order Traversal", "Post-order Traversal", "In-order Traversal", "Level-order Traversal"],
                    correct_answer_index=2,
                    explanation="In-order traversal visits left subtree, root, then right subtree, producing sorted output for a BST.",
                    topic=topic,
                    difficulty="Easy",
                ),
            ][:count]
        elif "oop" in topic_lower or "class" in topic_lower:
            return [
                PracticeQuestion(
                    question=f"Under '{topic}', which OOP principle allows a subclass to provide a specific implementation of a method defined in its superclass?",
                    options=["Encapsulation", "Polymorphism (Method Overriding)", "Multiple Inheritance", "Data Hiding"],
                    correct_answer_index=1,
                    explanation="Polymorphism through method overriding enables runtime dynamic dispatch for subclass-specific behaviors.",
                    topic=topic,
                    difficulty="Medium",
                ),
                PracticeQuestion(
                    question="Which design pattern ensures a class has only one instance while providing a global point of access to it?",
                    options=["Factory Pattern", "Observer Pattern", "Singleton Pattern", "Strategy Pattern"],
                    correct_answer_index=2,
                    explanation="The Singleton pattern restricts class instantiation to a single shared object instance.",
                    topic=topic,
                    difficulty="Easy",
                ),
            ][:count]
        elif "regression" in topic_lower or "data" in topic_lower or "machine" in topic_lower:
            return [
                PracticeQuestion(
                    question=f"Regarding '{topic}', which metric is most suitable for evaluating linear regression when large errors should be heavily penalized?",
                    options=["Mean Absolute Error (MAE)", "Root Mean Squared Error (RMSE)", "Accuracy", "F1-Score"],
                    correct_answer_index=1,
                    explanation="RMSE squares the errors before averaging and taking square root, disproportionately penalizing large residual errors.",
                    topic=topic,
                    difficulty="Medium",
                ),
                PracticeQuestion(
                    question="What regularization technique adds the absolute values of coefficients (L1 penalty) to prevent overfitting and induce feature sparsity?",
                    options=["Ridge Regression", "Lasso Regression", "ElasticNet", "Batch Normalization"],
                    correct_answer_index=1,
                    explanation="Lasso (L1) penalizes the sum of absolute coefficients, driving non-informative feature weights to exactly zero.",
                    topic=topic,
                    difficulty="Medium",
                ),
            ][:count]
        else:
            return [
                PracticeQuestion(
                    question=f"When analyzing '{topic}' in {course_name}, what is the primary prerequisite concept for understanding its core behavior?",
                    options=[
                        "Memorizing syntax edge-cases",
                        "Decomposing the underlying mathematical or logical invariants",
                        "Assuming average case equals worst case",
                        "Ignoring constraints and edge inputs",
                    ],
                    correct_answer_index=1,
                    explanation="Mastering invariant properties and decomposition allows systematic reasoning and problem solving under exam conditions.",
                    topic=topic,
                    difficulty="Medium",
                ),
                PracticeQuestion(
                    question=f"Which active learning strategy delivers the highest retention when studying '{topic}'?",
                    options=[
                        "Passive re-reading of slides",
                        "Highlighting lines in text multiple times",
                        "Retrieval practice by solving unassisted problems and flashcard self-testing",
                        "Listening to audio explanations while multitasking",
                    ],
                    correct_answer_index=2,
                    explanation="Empirical cognitive science shows active retrieval practice and problem-solving produce superior long-term neural recall.",
                    topic=topic,
                    difficulty="Easy",
                ),
            ][:count]
