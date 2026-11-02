"""Custom SaaS Styling for SyllabusPilot with Blue/Teal accents."""
import streamlit as st


def apply_custom_styles():
    """Injects modern SaaS CSS styles into the Streamlit application."""
    custom_css = """
    <style>
    /* Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Main Container background */
    .stApp {
        background-color: #f8fafc;
    }

    /* Clean Card */
    .sp-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.2rem;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .sp-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
    }

    /* Metric Cards */
    .sp-metric-box {
        background: #ffffff;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
        padding: 1.25rem;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03);
    }
    .sp-metric-title {
        font-size: 0.85rem;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.35rem;
    }
    .sp-metric-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #0f172a;
        line-height: 1.2;
    }
    .sp-metric-subtitle {
        font-size: 0.8rem;
        color: #0d9488;
        font-weight: 500;
        margin-top: 0.35rem;
    }

    /* Badges */
    .sp-badge {
        display: inline-block;
        padding: 0.25rem 0.65rem;
        font-size: 0.75rem;
        font-weight: 600;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.025em;
    }
    .badge-high {
        background-color: #fee2e2;
        color: #b91c1c;
        border: 1px solid #fecaca;
    }
    .badge-medium {
        background-color: #fef3c7;
        color: #b45309;
        border: 1px solid #fde68a;
    }
    .badge-low {
        background-color: #e0f2fe;
        color: #0369a1;
        border: 1px solid #bae6fd;
    }
    .badge-verified {
        background-color: #ccfbf1;
        color: #0f766e;
        border: 1px solid #99f6e4;
    }
    .badge-review {
        background-color: #ffedd5;
        color: #c2410c;
        border: 1px solid #fed7aa;
    }

    /* Hero Banner */
    .sp-hero {
        background: linear-gradient(135deg, #1e3a8a 0%, #0f766e 100%);
        color: white;
        padding: 2rem;
        border-radius: 14px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(15, 23, 42, 0.1);
    }
    .sp-hero h1 {
        color: #ffffff !important;
        font-weight: 700;
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    .sp-hero p {
        color: #e2e8f0;
        font-size: 1.05rem;
        margin-bottom: 0;
    }

    /* Custom Buttons */
    .stButton>button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.15s ease-in-out;
    }

    /* Streamlit data editor table styling */
    div[data-testid="stDataEditor"] {
        border-radius: 8px;
        border: 1px solid #e2e8f0;
        overflow: hidden;
    }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)
