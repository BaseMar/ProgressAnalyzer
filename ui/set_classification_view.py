"""Optional corrections inside recorded-session details, not a required workflow."""
import logging
import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from data_manager import DataManager
from mapper import map_workout_set
from metrics.set_interpretation import interpret_sets

logger = logging.getLogger(__name__)


def render_set_classification(manager=None, *, session_id=None):
    dm = manager if manager is not None else DataManager()
    with st.expander("Set interpretation · optional correction"):
        st.caption("Sets are interpreted automatically. Open an exception only when a recorded set was interpreted incorrectly.")
        if not st.toggle("Correct a set", key=f"set_exception_{session_id if session_id is not None else 'picker'}"):
            return
        try:
            if not dm.classification_storage_ready():
                st.info("Set labelling is not available until setup is complete.")
                return
            sid = session_id
            if sid is None:
                sessions = dm.load_sessions()
                if sessions.empty:
                    st.caption("No sessions to correct.")
                    return
                labels = {int(row.session_id): f'{pd.Timestamp(row.session_date):%d %b %Y} · Session #{row.session_id}' for row in sessions.itertuples()}
                sid = st.selectbox("Session to correct", list(labels), key="classify_session", format_func=labels.get)
            frame = dm.load_session_sets(sid)
            if frame.empty:
                st.caption("No sets in this session.")
                return
            meanings = interpret_sets([map_workout_set(row) for row in frame.to_dict("records")],
                                      deload_exercise_ids=dm.load_deload_exercise_ids())
            frame["Interpretation"] = [meaning.kind.replace("_", " ").capitalize() for meaning in meanings]
            frame["Source"] = [meaning.source.capitalize() for meaning in meanings]
            frame["Type"] = frame["is_warmup"].map(lambda value: "Auto" if pd.isna(value) else "Warm-up" if value else "Working")
            display = frame.rename(columns={"exercise_name": "Exercise", "set_number": "Set", "repetitions": "Reps", "weight": "kg", "duration_seconds": "Seconds"}).drop(columns="is_warmup")
            st.caption("Auto uses effort, sequence and deload context. Working/Warm-up overrides the inferred purpose; missing RIR remains unknown.")
            edited = st.data_editor(display, key=f"set_types_{sid}", hide_index=True, width="stretch",
                                    disabled=[column for column in display.columns if column != "Type"],
                                    column_config={"set_id": None, "workout_exercise_id": None,
                                                   "Type": st.column_config.SelectboxColumn("Override", options=["Auto", "Working", "Warm-up"], required=True)})
            if st.button("Save set labels", key=f"save_set_types_{sid}"):
                types = {"Auto": None, "Working": False, "Warm-up": True}
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
