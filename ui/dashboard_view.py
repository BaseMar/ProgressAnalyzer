"""Overview landing page; calendar implementation is owned by History."""
import streamlit as st
from data_manager import DataManager
from ui.history_view import HistoryView, _format_seconds, _set_pills
from ui.overview_view import OverviewView
from ui.utils.ui_helpers import page_title


class DashboardView(HistoryView):
    # Preserve the old constructor for callers; history rendering lives elsewhere.
    def __init__(self, metrics, sets_df, selected_month=None, *, exercise_names=None, data_manager=None):
        manager = data_manager if data_manager is not None else DataManager()
        super().__init__(metrics, sets_df, selected_month, exercise_names=exercise_names, data_manager=manager)

    def render(self, *, as_of=None):
        page_title("Overview", "Training Overview")
        OverviewView(self.dm, self.exercise_names).render(as_of=as_of)
