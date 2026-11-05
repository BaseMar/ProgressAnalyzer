"""Analytical overview with optional drill-down and source corrections."""
from calendar import monthrange
from datetime import date, timedelta
from html import escape
import logging
import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError
from data_manager import DataManager
from metrics.plan_adherence import compute_plan_adherence
from metrics.plan_performance import compute_plan_performance
from metrics.load_metrics import describe_load
from metrics.plan_summary import summarize_plan
from ui.utils.plan_charts import exercise_history_chart, weekly_execution_chart
from ui.utils.ui_helpers import chart_label, section_header
from metrics.training_block import deload_adjusted_input
from ui.utils.active_plan import select_active_plan

logger = logging.getLogger(__name__)


class PlanAdherenceView:
    def __init__(self, *, manager=None, exercise_names=None, selected_month=None):
        self.dm = manager if manager is not None else DataManager()
        self.names = exercise_names or {}
        self.selected_month = selected_month

    def _name(self, exercise_id):
        return self.names.get(exercise_id, f"Exercise #{exercise_id}")

    def render(self, *, mode="consistency"):
        if mode == "consistency":
            section_header("Plan consistency")
        try:
            if not self.dm.adherence_storage_ready():
                st.info("Plan analysis is not available until setup is complete.")
                return
            plans = {item.plan_id: item for item in self.dm.load_training_plans()}
            if not plans:
                st.info("Create a plan in Plan, then link sessions in History to start the analysis. Unplanned exercises are available under All recorded exercises.")
                return
            plan_id = select_active_plan(plans.values())
            versions = self.dm.load_training_plan_versions(plan_id)
            if self.selected_month not in (None, "All time"):
                start = date.fromisoformat(f"{self.selected_month}-01")
                end = start.replace(day=monthrange(start.year, start.month)[1])
            else:
                start = min(item.draft.effective_from for item in versions)
                end = max(date.today(), start) + timedelta(days=7)
            data = self.dm.load_plan_adherence(plan_id, start, end)
            history = self.dm.load_plan_performance(plan_id, start, end)
        except SQLAlchemyError:
            logger.exception("Unable to load plan analysis")
            st.error("Plan analysis could not be loaded. Please try again.")
            return
        block_settings = {version.version_id: version.draft.progression for version in versions}
        report = compute_plan_adherence(deload_adjusted_input(data, block_settings, as_of=date.today()),
                                        as_of=date.today(), settings_by_version=block_settings)
        performance = compute_plan_performance(history, as_of=date.today(), start=start, end=end,
                                             settings_by_version=block_settings)
        if mode == "exercise":
            self.render_performance(performance)
            return
        overview, summary = summarize_plan(report, performance), report["summary"]
        st.markdown('<div class="analysis-insight">'
                    f'<strong>{summary["linked_workouts"]} of {summary["due_workouts"]} elapsed workouts have linked logs.</strong><br>'
                    f'{summary["covered_sets"]} of {summary["planned_sets"]} planned sets are logged; '
                    f'{overview["in_range"]} of {overview["recorded_sets"]} logged sets are within range.</div>', unsafe_allow_html=True)
        if not summary["due_workouts"]:
            st.info("No elapsed planned days in this period. Today and future dates are excluded.")
        else:
            chart_label("Weekly execution")
            st.plotly_chart(weekly_execution_chart(overview["weeks"]), width="stretch", key="weekly_plan_execution")
        st.caption("Completed calendar days only. An unlinked workout is not proof that it was skipped.")
        if any(row["training_phase"] == "deload" for row in performance):
            st.caption("Deload dates use reduced set/repetition targets for resistance exercises. Deload logs are excluded from exercise progress comparisons.")
        with st.expander("Definitions & source data"):
            st.caption(f'On the planned day: {summary["on_time_workouts"]}/{summary["linked_workouts"]} linked workouts. RIR missing: {overview["missing_rir"]}/{overview["recorded_sets"]} logged sets.')
            st.caption("Coverage uses inferred or explicitly marked working sets, plus unknown-effort and timed logs; deload uses its own targets. Light/low-effort work stays in history. Missing RIR is not zero. These indicators do not measure technique or muscle growth.")
            if report["workouts"]:
                st.dataframe(pd.DataFrame([{"Planned date": row["scheduled_date"], "Workout": row["name"], "Recorded date": row["performed_on"], "Status": row["status"], "Sets logged": row["covered_sets"], "Sets planned": row["planned_sets"]} for row in report["workouts"]]), hide_index=True, width="stretch")

    @staticmethod
    def _set_label(item, unit):
        quantity = f'{item["seconds"]}s' if unit == "seconds" else f'{item["reps"]} reps'
        if item.get("load_type", "legacy") != "legacy":
            return f'{quantity} @ {describe_load(item)} · RIR {item["rir"] if item["rir"] is not None else "?"}'
        load = f' @ {item["weight"]:g} kg' if item["weight"] else ""
        return f'{quantity}{load} · RIR {item["rir"] if item["rir"] is not None else "?"}'

    def render_performance(self, rows):
        section_header("Exercise trends")
        observed = [row for row in rows if row["sets"]]
        if not observed:
            st.caption("No matching logs in this period. Link a session or confirm a replacement to see its trend.")
            return
        contexts = list(dict.fromkeys(row["context"] for row in observed))
        selected = st.selectbox("Explore an exercise", contexts, key="performance_context", format_func=lambda key: f'{key[0]} · {self._name(key[5])} · {key[7]} × {key[8]}–{key[9]} {key[6]} · position {key[3]}')
        selected_rows = [row for row in observed if row["context"] == selected]
        latest = selected_rows[-1]
        st.markdown(f'<div class="analysis-insight">{escape(latest["comparison"])}</div>', unsafe_allow_html=True)
        st.caption(f'Last recorded {latest["performed_on"]:%d %b %Y} · {latest["in_range"]}/{latest["planned_sets"]} sets in range · {latest["rir_status"]}')
        fig = exercise_history_chart(selected_rows)
        if fig is not None:
            st.plotly_chart(fig, width="stretch", key="plan_exercise_history")
        st.caption("Shaded band = target range at each date; amber diamonds = deload. Means describe logged sets, including partial sessions. Read load alongside reps/time; substitutes keep separate histories.")
        st.caption("Explicit bodyweight logs use body mass + additional weight − measured assistance. "
                   "Unknown loads and convention changes are not graded; less assistance increases difficulty.")
        with st.expander("Previous vs current · set breakdown"):
            previous = latest["previous"]
            if previous:
                st.caption(f'Previous: {previous["performed_on"]:%d %b %Y} · Current: {latest["performed_on"]:%d %b %Y}. History may extend outside the selected month.')
            else:
                st.caption("No prior execution with the same workout context and targets.")
            old_sets = previous["sets"] if previous else ()
            st.dataframe(pd.DataFrame([{"Set": index + 1, "Previous": self._set_label(old_sets[index], latest["unit"]) if index < len(old_sets) else "—", "Current": self._set_label(latest["sets"][index], latest["unit"]) if index < len(latest["sets"]) else "—"} for index in range(latest["planned_sets"])]), hide_index=True, width="stretch")
            st.caption("Changed loads and incomplete counts are not automatically graded. Missing RIR stays unknown. Context or target changes start a new history.")
