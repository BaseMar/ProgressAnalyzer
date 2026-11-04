"""Explicit set-type corrections, hidden from the analytical overview."""
import logging
import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from data_manager import DataManager

logger = logging.getLogger(__name__)


def render_set_classification(manager=None):
    dm = manager if manager is not None else DataManager()
    with st.expander("Working sets & warm-up labels"):
        try:
            if not dm.classification_storage_ready():
                st.info("Set labelling is not available until setup is complete.")
                return
            sessions = dm.load_sessions()
            if sessions.empty:
                st.caption("No sessions to classify.")
                return
            labels = {int(row.session_id): f'{pd.Timestamp(row.session_date):%d %b %Y} · Session #{row.session_id}' for row in sessions.itertuples()}
            sid = st.selectbox("Session to classify", list(labels), key="classify_session", format_func=labels.get)
            frame = dm.load_session_sets(sid)
            if frame.empty:
                st.caption("No sets in this session.")
                return
            frame["Type"] = frame["is_warmup"].map(lambda value: "Unknown" if pd.isna(value) else "Warm-up" if value else "Working")
            display = frame.rename(columns={"exercise_name": "Exercise", "set_number": "Set", "repetitions": "Reps", "weight": "kg", "duration_seconds": "Seconds"}).drop(columns="is_warmup")
            st.caption("Only explicit warm-ups are excluded. Unknown history stays included; no labels are guessed from weight or position.")
            edited = st.data_editor(display, key=f"set_types_{sid}", hide_index=True, width="stretch",
                                    disabled=[column for column in display.columns if column != "Type"],
                                    column_config={"set_id": None, "Type": st.column_config.SelectboxColumn(options=["Unknown", "Working", "Warm-up"], required=True)})
            if st.button("Save set labels", key=f"save_set_types_{sid}"):
                types = {"Unknown": None, "Working": False, "Warm-up": True}
                if not edited["Type"].isin(types).all():
                    raise ValueError("Choose a type for every set before saving")
                dm.save_set_classifications(sid, {int(row.set_id): types[row.Type] for row in edited.itertuples()})
                st.cache_data.clear()
                st.rerun()
        except ValueError as exc:
            st.error(str(exc))
        except SQLAlchemyError:
            logger.exception("Set classification failed")
            st.error("Set labels could not be loaded or saved. Please try again.")
