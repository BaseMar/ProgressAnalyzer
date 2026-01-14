import streamlit as st
import pandas as pd

def render_sessions_tab(metrics):
    """
    Render the Sessions tab with per-session metrics and global aggregates.
    metrics: dict zawierający metryki wygenerowane przez compute_all_metrics
    """

    st.header("Sesje treningowe")

    # --- Globalne wskaźniki ---
    global_metrics = metrics["sessions"]["global"]
    col1, col2, col3 = st.columns(3)
    col1.metric("Śr. czas sesji (min)", round(global_metrics.get("avg_session_duration", 0), 1))
    col2.metric("Śr. objętość / sesja", round(global_metrics.get("avg_volume_per_session", 0), 1))
    col3.metric("Śr. liczba serii / sesja", round(global_metrics.get("avg_sets_per_session", 0), 1))

    st.markdown("---")

    # --- Tabela per-session ---
    per_session = metrics["sessions"]["per_session"]
    if per_session:
        session_df = pd.DataFrame.from_dict(per_session, orient="index")
        session_df.index.name = "Session ID"
        session_df.reset_index(inplace=True)
        st.dataframe(session_df)
    else:
        st.info("Brak danych sesji do wyświetlenia.")
