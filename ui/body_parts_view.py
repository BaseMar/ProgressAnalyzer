"""
Body Parts view for the UI layer.

Provides a high-level overview of training distribution
across body parts (volume, sets, strength proxy).

This view is intentionally macro-oriented:
- no drill-downs
- no time trends
- no session-level logic
"""

from typing import Dict
import streamlit as st
from ui.utils.body_parts_df import build_body_parts_df


class BodyPartsView:
    """
    UI view responsible for presenting body-part-level insights.

    Data source:
    - metrics["exercises"]["per_exercise"]

    Responsibilities:
    - KPI overview
    - volume distribution charts
    - comparative table
    """

    def __init__(self, exercises_metrics: Dict):
        self.exercises_metrics = exercises_metrics

    def render(self) -> None:
        """Render the Body Parts view."""
        st.header("Body Parts")

        body_df = build_body_parts_df(self.exercises_metrics)

        if body_df.empty:
            st.info("No body part data available.")
            return

        # --- KPI ---
        kpi_cols = st.columns(4)

        total_parts = len(body_df)
        most_trained = body_df.iloc[0]["Body Part"]
        least_trained = body_df.iloc[-1]["Body Part"]
        avg_volume = body_df["Total_Volume"].mean()

        kpi_cols[0].metric("Body Parts", total_parts)
        kpi_cols[1].metric("Most Trained", most_trained)
        kpi_cols[2].metric("Least Trained", least_trained)
        kpi_cols[3].metric("Avg Volume / Part", int(avg_volume))

        # --- Charts ---
        st.subheader("Training Distribution")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Total Volume per Body Part**")
            st.bar_chart(body_df.set_index("Body Part")["Total_Volume"], height=320)

        with col2:
            st.markdown("**Sessions by Body Part**")
            st.bar_chart(body_df.set_index("Body Part")[["Sessions"]], height=320)


        # --- Comparative Table ---
        st.subheader("Body Part Comparison")

        table_df = body_df.rename(columns={
            "Body Part": "Body Part",
            "Total_Sets": "Total Sets",
            "Total_Volume": "Total Volume",
            "Avg_1RM": "Avg 1RM",
        })

        st.dataframe(table_df,
            column_config={
                "Avg 1RM": st.column_config.NumberColumn(format="%.2f"),
                "Total Volume": st.column_config.NumberColumn(format="%.0f"),
            }, width="stretch")
