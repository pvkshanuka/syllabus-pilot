# 🎓 SyllabusPilot — AI-Powered Autonomous Study Planning Agent

> **Built for the GDG Riga AI Agents Hackathon**  
> Transform university course syllabi (PDF, images, text) into personalized, conflict-free weekly study plans with Google Calendar export, dynamic recovery, workload balancing, and an AI Study Coach.

---

## 🌟 Why SyllabusPilot?

University syllabi are dense, fragmented documents packed with assessment deadlines, weighted percentages, and sprawling reading lists. Students struggle with:
1. **Deadline Blindspots**: Missing critical midterms or assignments buried in 15-page syllabus PDFs.
2. **Poor Pacing**: Cramming at the last minute because study effort wasn't scheduled in advance.
3. **Fragile Plans**: Giving up entirely when sickness or emergencies disrupt their schedule for a few days.

**SyllabusPilot** is an autonomous agent that bridges the gap between static academic documents and actionable daily student execution.

---

## 🚀 Key Features

### 1. Multimodal Syllabus Extraction (Gemini 3.8 Flash)
- Upload university syllabi as **PDF documents**, **scanned photos (JPG/PNG)**, or **raw pasted text**.
- Extracts:
  - Course metadata (Course Name, Code, Instructor, Semester Dates)
  - Graded Assessments (Assignments, Midterms, Finals, Projects, Quizzes)
  - Hard deadlines and grade weight percentages
  - Course outline topics and syllabus chapters
- **Security & Integrity**: Treats syllabus content as untrusted document data with prompt injection defense. Never invents or hallucinates dates—missing items are flagged as `"Needs Review"`.
- **Interactive Review Table**: Clean, editable table allowing students to inspect and tweak extracted dates or weights before generating a schedule.

### 2. 3-Question Personalization Wizard
Generates a realistic, conflict-free schedule with at most three questions:
1. **Weekly Availability**: How many hours can you study per week? (e.g., 10 hrs/week)
2. **Available Days**: Which days are you free? (e.g., Monday, Wednesday, Friday, Sunday)
3. **Preferred Study Time**: When do you focus best? (Morning 09:00, Afternoon 14:00, Evening 18:30, Night 20:30)

### 3. Deterministic Scheduling Engine
- Deterministic Python constraint satisfaction algorithm:
  - **Deadlines**: Sessions are strictly scheduled *before* each assessment's deadline.
  - **No Conflicts**: Zero overlapping study blocks.
  - **Spaced Repetition**: Spaced preparation sessions spread over weeks leading up to deliverables.
  - **Revision Blocks**: Automatically reserves dedicated revision sessions prior to major examinations.

### 4. Adaptive Study Recovery Agent
*Life happens — students get sick or miss sessions.*
- Automatically detects overdue uncompleted study blocks.
- Calculates remaining available hours without exceeding weekly capacity.
- **Preserves Completed Sessions**: Never touches or undos work you've already finished.
- **Before-and-After Visual Diff**: Shows a side-by-side comparison of the old vs. new schedule with a narrative explanation.
- **Requires Confirmation**: Requires explicit user approval before applying changes to the schedule.

### 5. Smart Priority & Workload Balancer
- Transparent multi-factor assessment priority score (0 to 100):
  - **Deadline Proximity** (40 pts)
  - **Grading Weight %** (35 pts)
  - **Estimated Effort** (15 pts)
  - **Incompletion Ratio** (10 pts)
- Categorizes assessments into **High**, **Medium**, and **Low** priority tiers.
- Proactively flags overloaded calendar weeks and suggests shifting preparation earlier.

### 6. AI Study Coach & Practice Quizzes
- **Conversational Mentor**: Powered by Google Gemini and Google ADK agent patterns to answer student questions.
- **Active Recall Quizzes**: Generates topic-specific multiple-choice practice quizzes derived directly from syllabus concepts with instant pedagogical feedback and explanations.
- **Strategy Tips**: Provides concise active recall and memory retention advice (Feynman technique, active recall).

### 7. Google Calendar (.ICS) Integration
- Generates RFC 5545 compliant `.ics` calendar files.
- Includes unique event IDs (`UID`), course references, target assessments, and customizable timezone support (`Europe/Riga`, `America/New_York`, `UTC`, etc.).
- Includes both study sessions and deadline reminders.
- Compatible with Google Calendar, Apple Calendar, and Outlook.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| **Runtime** | Python 3.11+ |
| **LLM & Agent Framework** | Official Google Gen AI SDK (`google-genai` 2.34.0) & ADK agent patterns |
| **Frontend UI** | Streamlit 1.66.1 (Modern Blue/Teal SaaS Theme) |
| **Data Validation** | Pydantic v2 (Strict Schema Enforcement) |
| **Calendar Engine** | `icalendar` 7.3.0 (RFC 5545 Specification) |
| **Persistence** | SQLite with WAL mode and foreign key cascades |
| **Testing** | Pytest (17 automated unit and end-to-end tests) |

---

## 📂 Project Architecture

```
syllabus-pilot/
├── app.py                     # Streamlit application entry point & routing
├── agent/
│   ├── agent.py               # SyllabusPilotAgent orchestrator
│   ├── prompts.py             # System prompts (Extraction, Coach, Security)
│   └── tools.py               # 8 Callable registered tools
├── services/
│   ├── extraction.py          # Multimodal syllabus parser (PDF, Image, Text)
│   ├── scheduling.py          # Deterministic study scheduler
│   ├── priority.py            # Workload balancer & priority scoring engine
│   ├── replanning.py          # Adaptive recovery engine (missed session redistribution)
│   ├── calendar_export.py     # RFC 5545 ICS calendar exporter
│   └── study_coach.py         # AI study coach & topic practice quiz generator
├── models/
│   ├── schemas.py             # Pydantic data schemas
│   └── database.py            # SQLite database initialization & tables
├── repositories/
│   ├── course_repository.py   # Course & assessment CRUD operations
│   └── study_repository.py    # Plan, session, completion & recovery history CRUD
├── ui/
│   ├── styles.py              # SaaS CSS styling (Blue/Teal accents, rounded cards)
│   ├── dashboard.py           # Dashboard overview, stat cards, next session card
│   ├── upload.py              # Multimodal upload & editable assessment table
│   ├── planner.py             # 3-question wizard, study calendar, ICS download
│   ├── recovery.py            # Adaptive study recovery & before/after comparison
│   ├── coach.py               # AI coach chat, priority balancer & practice quizzes
│   └── settings.py            # Gemini API keys, timezone, and database diagnostics
├── samples/
│   ├── sample_cs101_syllabus.txt        # Full CS101 sample syllabus
│   └── sample_datascience_syllabus.txt  # Full DS301 Data Science sample syllabus
├── tests/
│   ├── test_database.py       # Database & repository CRUD tests
│   ├── test_extraction.py     # Text, PDF, regex, and prompt injection tests
│   ├── test_scheduling.py     # Constraint satisfaction, deadline & overlap tests
│   ├── test_calendar.py       # Valid RFC 5545 ICS format & parsing tests
│   ├── test_priority.py       # Multi-factor priority score & overload tests
│   ├── test_replanning.py     # Adaptive recovery & preservation tests
│   ├── test_agent.py          # Agent tool coordination & intent routing tests
│   └── test_e2e_flow.py       # Complete 11-step end-to-end integration test
├── pytest.ini                 # Pytest configuration
├── requirements.txt           # Project dependencies
├── .env.example               # Environment variables template
└── README.md                  # Documentation & hackathon presentation guide
```

---

## ⚡ Quickstart Guide

### 1. Prerequisites
- Python 3.11 or later
- Google Gemini API Key ([Get one free at Google AI Studio](https://aistudio.google.com))

### 2. Installation
```powershell
# Clone or navigate to the project directory
cd C:\Users\Kusal\.gemini\antigravity\scratch\syllabus-pilot

# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy `.env.example` to `.env` and insert your Gemini API Key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
DEFAULT_TIMEZONE=Europe/Riga
GEMINI_MODEL=gemini-3.8-flash
```
*(Note: SyllabusPilot includes a built-in deterministic fallback parser so you can explore and test the entire workflow even before entering an API key).*

### 4. Run Automated Test Suite
```powershell
pytest -v
```
*Expected: 17 passed tests in ~3 seconds.*

### 5. Launch the Application
```powershell
streamlit run app.py
```
Open [http://localhost:8501](http://localhost:8501) in your web browser.

---

## 🎯 5-Minute Live Demo Walkthrough (for Hackathon Judges)

1. **Upload & Extract (Minute 1)**:
   - Go to **📄 Upload & Extract Syllabus**.
   - Click **"📥 Load CS101: Computer Science Syllabus"** or upload any syllabus PDF/photo.
   - Click **"🔍 Analyze Pasted Syllabus"**.
   - Watch Gemini extract the course code, 7 assessments, exact ISO deadlines, grading weights, and weekly topics.
   - Edit any row in the interactive table (e.g. adjust a percentage or date) and click **"Confirm & Save"**.

2. **Generate Study Plan & Export Calendar (Minute 2)**:
   - Go to **📅 Study Planner & ICS**.
   - Answer the 3 personalization questions: 10 hours/week, Mon/Wed/Fri/Sun, Evening.
   - Click **"🚀 Generate Autonomous Study Schedule"**.
   - Inspect the generated week-by-week sessions with topics and final revision blocks.
   - Click **"📥 Download .ICS"** and view the generated calendar file.

3. **Simulate Life Disruption & Adaptive Recovery (Minute 3)**:
   - In **Study Planner**, check off 2 sessions as "Done".
   - Go to **🔄 Adaptive Study Recovery**.
   - Enter reason: *"I had the flu for 3 days and missed my study sessions"*.
   - Click **"🔍 Calculate Recovery Plan & Compare"**.
   - Point out the **Before vs. After Comparison**: completed sessions were preserved, missed sessions were seamlessly rescheduled into future slots before the deadline.
   - Click **"Confirm & Apply Recovered Schedule"**.

4. **Workload Balancer & AI Coach (Minute 4)**:
   - Go to **💡 AI Study Coach & Quizzes**.
   - Switch to **⚖️ Smart Priority & Workload Balancer** to view transparent 0-100 priority scores and capacity metrics.
   - Switch to **🎯 Topic Practice Quiz**, choose *"Recursion"*, and click **"Generate 3 Practice Questions"**.
   - Answer the interactive quiz questions to demonstrate pedagogical explanations.

5. **Dashboard & Restart Persistence (Minute 5)**:
   - Head back to **📊 Dashboard Overview** to view overall completion %, hours remaining, and next recommended study session.
   - Restart the app or reload the page: all data remains saved in SQLite!

---

## 🏆 Hackathon Compliance Checklist

| Mandatory Requirement | Status | Evidence |
|---|---|---|
| Accept PDF, photo, or pasted text | ✅ COMPLETE | Multimodal PDF/Image/Text support in `services/extraction.py` |
| Extract assessment names, deadlines, weights, topics | ✅ COMPLETE | Pydantic validated output in `models/schemas.py` |
| Clean editable table for extracted data | ✅ COMPLETE | `st.data_editor` in `ui/upload.py` |
| Maximum of three personalization questions | ✅ COMPLETE | Hours/week, available days, preferred time in `ui/planner.py` |
| Week-by-week study schedule generation | ✅ COMPLETE | `services/scheduling.py` constraint satisfaction algorithm |
| Export valid `.ics` calendar file | ✅ COMPLETE | RFC 5545 compliant export in `services/calendar_export.py` |
| Google Calendar compatibility | ✅ COMPLETE | Verified with timezone, UIDs, categories, and import instructions |
| Adaptive Study Recovery Agent | ✅ COMPLETE | Replan with Before/After diff & user confirmation in `services/replanning.py` |
| Smart Priority & Workload Balancer | ✅ COMPLETE | Multi-factor scoring (0-100) & overload warnings in `services/priority.py` |
| AI Study Coach & Practice Quizzes | ✅ COMPLETE | Active recall quizzes & pedagogical tips in `services/study_coach.py` |
| Local persistence | ✅ COMPLETE | SQLite schema with foreign key cascades in `models/database.py` |
| Automated testing | ✅ COMPLETE | 17 automated tests passing in Pytest |

---

## 📜 License
MIT License. Built with ❤️ for GDG Riga AI Agents Hackathon.
