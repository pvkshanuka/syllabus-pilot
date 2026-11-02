"""UI Module for SyllabusPilot."""
from .styles import apply_custom_styles
from .dashboard import render_dashboard
from .upload import render_upload_page
from .planner import render_planner_page
from .recovery import render_recovery_page
from .coach import render_coach_page
from .settings import render_settings_page

__all__ = [
    "apply_custom_styles",
    "render_dashboard",
    "render_upload_page",
    "render_planner_page",
    "render_recovery_page",
    "render_coach_page",
    "render_settings_page",
]
