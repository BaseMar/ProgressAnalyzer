"""
Body Parts view for the UI layer.

Provides a high-level overview of training distribution
across body parts based on exercise-level metrics.
"""

from typing import Dict
import pandas as pd
import streamlit as st


class BodyPartsView:
    """
    UI view responsible for body-part-level insights.

    Source:
    - exercises_metrics["per_exercise"]

    Responsibilities:
    - KPI overview
    - distribution charts
    - comparison table
    """

    def __init__(self, exercises_metrics: Dict):
        self.exercises_metrics = exercises_metrics

    def _build_bodypart_df(self) -> pd.DataFrame:
        """
        Aggregate exercise metrics per body part.

        Returns
        -------
        pd.DataFrame
            Aggregated metrics per body part.
        """
        per_exercise = self.exercises_metrics.get("per_exercise", {})

        if not per_exercise:
            return pd.DataFrame()

        df = pd.DataFrame(per_exercise).T

        # Drop exercises without body part
        df = df.dropna(subset=["body_part"])

        body_df = (
            df.groupby("body_part")
            .agg(
                Total_Sets=("total_sets", "sum"),
                Total_Volume=("total_volume", "sum"),
                Sessions=("sessions_count", "sum"),
                Avg_1RM=("estimated_1rm_avg", "mean"),
            )
            .reset_index()
            .rename(columns={"body_part": "Body Part"})
            .sort_values("Total_Volume", ascending=False)
        )

        return body_df

    def render(self) -> None:
        """Render Body Parts view."""
        st.header("Body Parts")

        body_df = self._build_bodypart_df()

        if body_df.empty:
            st.info("No body part data available.")
            return

        # ---------- KPI ----------
        st.subheader("Overview")

        total_parts = len(body_df)
        most_trained = body_df.iloc[0]["Body Part"]
        least_trained = body_df.iloc[-1]["Body Part"]
        avg_volume = body_df["Total_Volume"].mean()

        kpi_cols = st.columns(4)

        kpi_cols[0].metric("Body Parts Trained", total_parts)
        kpi_cols[1].metric("Most Trained", most_trained)
        kpi_cols[2].metric("Least Trained", least_trained)
        kpi_cols[3].metric("Avg Volume / Part", int(avg_volume))

        # ---------- Charts ----------
        st.subheader("Training Distribution")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Volume per Body Part**")
            st.bar_chart(body_df.set_index("Body Part")["Total_Volume"], height=320)

        with col2:
            st.markdown("**Avg 1RM per Body Part**")
            st.bar_chart(body_df.set_index("Body Part")["Avg_1RM"], height=320,)

        # ---------- Table ----------
        st.subheader("Body Part Comparison")

        st.dataframe(
            body_df,
            column_config={
                "Total_Volume": st.column_config.NumberColumn(format="%.0f"),
                "Avg_1RM": st.column_config.NumberColumn(format="%.2f"),
            },
            width="stretch",
        )
