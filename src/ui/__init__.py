"""UI components for the Streamlit dashboard."""

from .auth import handle_authentication
from .dashboard import render_dashboard

__all__ = ['handle_authentication', 'render_dashboard']