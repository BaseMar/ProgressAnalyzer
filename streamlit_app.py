"""Load source data and route to Overview, Analysis, Plan or History.

Database services own persistence, pure metrics modules own decision rules,
and views prepare the selected analytical question for display. Historical
filters stay local; they never change the upcoming training prescription.
"""

from pathlib import Path

import streamlit as st

from data_loader import load_data
from data_manager import DataManager
from db.read_cache import read_scope
from metrics.measurement_timeline import measurement_timeline
from ui.analysis_view import AnalysisView
from ui.history_view import HistoryView
from ui.overview_view import OverviewView
from ui.sidebar_view import SidebarView
from ui.training_plan_view import TrainingPlanView
from ui.utils.ui_helpers import page_title


def _configure_page() -> None:
    """Configure Streamlit page settings (title, layout, sidebar state)."""
    st.set_page_config(
        page_title="Workout Progress Analyzer",
        page_icon="💪",
        layout="wide",
        initial_sidebar_state="expanded",
    )


def _load_global_styles() -> None:
    """Inject main.css into the Streamlit page."""
    css_path = Path(__file__).resolve().parent / "ui" / "styles" / "main.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    else:
        st.error(f"CSS NOT FOUND: {css_path}")


@read_scope()
def main() -> None:
    """Load source data, then render one task; historical filters belong to Analysis."""
    _load_global_styles()

    try:
        raw_input_data, sets_dataframe = load_data()
    except Exception as exc:
        st.error(f"Failed to load data: {exc}")
        st.stop()

    sidebar = SidebarView()
    selected_page = sidebar.render_navigation()
    names = {exercise.exercise_id: exercise.name for exercise in raw_input_data.exercises}
    if selected_page == "Overview":
        page_title("Overview", "Training Overview")
        OverviewView(DataManager(), names).render()
    elif selected_page == "Analysis":
        AnalysisView(raw_input_data, sets_dataframe, exercise_names=names).render()
    elif selected_page == "Plan":
        TrainingPlanView(raw_input_data.exercises).render()
    else:
        HistoryView(
            {"body": {"timeline": measurement_timeline(raw_input_data)}},
            sets_dataframe,
            exercise_names=names,
        ).render()

    st.markdown(
        '<div class="app-footer">Workout Progress Analyzer · Recorded results and explained training targets.</div>',
        unsafe_allow_html=True,
    )


def run(*, demo=False):
    _configure_page()
    if not demo:
        main()
        return
    from db.connection import database_scope
    from db.public_demo import session_demo_database

    database = session_demo_database()
    with database_scope(database.engine, database.cache_key):
        with st.container(key="public_demo_notice"):
            st.info("Interactive demo · Fictional data · Changes last for this browser session")
        if st.sidebar.button("Reset demo", key="reset_public_demo"):
            load_data.clear(database.cache_key)
            session_demo_database.clear()
            st.session_state.clear()
            st.rerun()
        main()


if __name__ == "__main__":
    run(demo=True)
