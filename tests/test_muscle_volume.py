"""Plan-based muscle allocation with no manual or synthetic targets."""

from dataclasses import replace
from datetime import date, timedelta

import pandas as pd
from sqlalchemy.exc import SQLAlchemyError

from db.training_plans import save_training_plan
from metrics.muscle_distribution import build_weekly_distribution
from metrics.muscle_volume import weekly_plan_sets
from models.training_plan import PlannedExercise, TrainingDay, TrainingPlanDraft
from test_navigation_journeys import start_app
from test_plan_schedule import schedule_data as schedule_data
from ui.body_parts_view import BodyPartsView


def test_weekly_targets_count_every_day_and_secondary_allocation(sample_input):
    draft = TrainingPlanDraft(
        "Full Body",
        date.today(),
        tuple(
            TrainingDay(
                "Full body",
                weekday,
                (
                    PlannedExercise(1, 3, 6, 10),
                    PlannedExercise(2, 4, 6, 10),
                ),
            )
            for weekday in (0, 2, 4)
        ),
    )
    totals, missing = weekly_plan_sets(draft, sample_input)
    assert totals == {"Chest": 9.0, "Triceps": 4.5, "Back": 12.0}
    assert not missing


def test_body_part_fallback_and_unknown_mapping_are_explicit(sample_input):
    draft = TrainingPlanDraft(
        "Test",
        date.today(),
        (TrainingDay("Test", 0, (PlannedExercise(1, 3, 6, 10), PlannedExercise(999, 2, 6, 10))),),
    )
    totals, missing = weekly_plan_sets(draft, replace(sample_input, exercise_muscle_targets=[]))
    assert totals == {"Chest": 3.0}
    assert missing == {999}


def test_summary_does_not_clamp_plan_or_invent_target():
    empty = pd.DataFrame(columns=["Body Part", "Total_Sets"])
    table = build_weekly_distribution(empty, 1.0, {"Chest": 4.5, "Back": 30.0}).set_index(
        "Body Part"
    )
    assert table.loc["Chest", "Target"] == 4.5
    assert table.loc["Back", "Target"] == 30.0
    assert table.loc["Calves", "Target"] == 0.0
    assert build_weekly_distribution(empty, 1.0)["Target"].isna().all()


def test_timed_sets_are_separate_from_dynamic_distribution():
    view = BodyPartsView(
        {
            "per_exercise": {
                1: {
                    "body_part": "Abs",
                    "total_sets": 2,
                    "effective_sets": 6.0,
                    "dynamic_sets": 0,
                    "timed_sets": 2,
                    "total_volume": 0.0,
                }
            }
        }
    )
    row = view._build_bodypart_df().iloc[0]
    assert row["Total_Sets"] == 0.0
    assert row["Timed_Sets"] == 2.0


def ranges_table(app):
    return app.dataframe[0].value.set_index("Body Part")


def open_muscle_distribution(schedule_data, sample_input, sets_dataframe):
    app = start_app(schedule_data, sample_input, sets_dataframe, page="Analysis")
    app.session_state["analysis_tab"] = "Muscles"
    app.run()
    assert not app.exception
    assert not app.error
    return app


def test_new_plan_is_activated_and_recalculates_targets_across_navigation(
    schedule_data, sample_input, sets_dataframe
):
    app = open_muscle_distribution(schedule_data, sample_input, sets_dataframe)
    assert ranges_table(app).loc["Chest", "Target"] == 3.0
    assert ranges_table(app).loc["Triceps", "Target"] == 1.5
    assert not app.get("data_editor")
    app.button(key="nav_Plan").click().run()
    app.button(key="plan_create_new").click().run()
    app.text_input(key="plan_editor_new_name").set_value("Full Body")
    app.text_input(key="plan_editor_new_day_0_name").set_value("Full Body A")
    app.selectbox(key="plan_editor_new_day_0_ex_0_exercise_id").select(1)
    app.number_input(key="plan_editor_new_day_0_ex_0_sets").set_value(7)
    app.button(key="plan_editor_new_save").click().run()
    assert not app.exception and not app.error
    # AppTest needs a clean render after the save's internal st.rerun.
    app.run()
    new_plan = app.session_state["active_plan_id"]
    assert new_plan != schedule_data[2].plan_id
    app.button(key="nav_Analysis").click().run()
    app.session_state["analysis_tab"] = "Muscles"
    app.run()
    assert not app.exception
    assert ranges_table(app).loc["Chest", "Target"] == 7.0
    assert ranges_table(app).loc["Triceps", "Target"] == 3.5
    app.selectbox(key="adherence_plan").select(schedule_data[2].plan_id).run()
    assert ranges_table(app).loc["Chest", "Target"] == 3.0
    app.selectbox(key="analysis_month").select("2026-05").run()
    assert ranges_table(app).loc["Chest", "Target"] == 3.0


def test_future_revision_does_not_replace_current_target(
    schedule_data, sample_input, sets_dataframe
):
    engine, _, plan, _ = schedule_data
    save_training_plan(
        engine,
        replace(
            plan.draft,
            effective_from=date.today() + timedelta(days=7),
            days=(TrainingDay("Future", 0, (PlannedExercise(1, 20, 6, 10),)),),
        ),
        plan_id=plan.plan_id,
    )
    app = open_muscle_distribution(schedule_data, sample_input, sets_dataframe)
    assert ranges_table(app).loc["Chest", "Target"] == 3.0


def test_future_plan_has_no_target(schedule_data, sample_input, sets_dataframe):
    engine, _, plan, _ = schedule_data
    future = save_training_plan(
        engine, replace(plan.draft, name="Future", effective_from=date.today() + timedelta(days=7))
    )
    app = open_muscle_distribution(schedule_data, sample_input, sets_dataframe)
    app.selectbox(key="adherence_plan").select(future.plan_id).run()
    assert not app.exception
    assert pd.isna(ranges_table(app).loc["Chest", "Target"])
    assert any("not started" in item.value for item in app.info)


def test_no_plans_still_shows_reference_without_targets(
    schedule_data, sample_input, sets_dataframe
):
    from db.training_plans import days, exercises, plans, versions

    engine = schedule_data[0]
    with engine.begin() as connection:
        connection.execute(exercises.delete())
        connection.execute(days.delete())
        connection.execute(versions.delete())
        connection.execute(plans.delete())
    app = open_muscle_distribution(schedule_data, sample_input, sets_dataframe)
    assert pd.isna(ranges_table(app).loc["Chest", "Target"])
    assert ranges_table(app).loc["Chest", "Recorded / week"] > 0


def test_plan_read_failure_keeps_reference_visible(
    schedule_data, sample_input, sets_dataframe, monkeypatch
):
    from data_manager import DataManager

    app = open_muscle_distribution(schedule_data, sample_input, sets_dataframe)

    def fail(_):
        raise SQLAlchemyError("Unavailable")

    monkeypatch.setattr(DataManager, "load_training_plans", fail)
    app.run()
    assert not app.exception and not app.error
    assert pd.isna(ranges_table(app).loc["Chest", "Target"])
    assert any("could not be loaded" in item.value for item in app.warning)


def test_plan_target_visible_before_first_logged_workout(
    schedule_data, sample_input, sets_dataframe
):
    empty = replace(sample_input, sessions=[], workout_exercises=[], sets=[])
    app = open_muscle_distribution(schedule_data, empty, sets_dataframe.iloc[:0])
    assert ranges_table(app).loc["Chest", "Target"] == 3.0
    assert ranges_table(app).loc["Triceps", "Target"] == 1.5


def test_incomplete_mapping_does_not_show_partial_target(
    schedule_data, sample_input, sets_dataframe
):
    unmapped = replace(
        sample_input,
        exercises=[
            replace(item, body_part=None) if item.exercise_id == 1 else item
            for item in sample_input.exercises
        ],
        exercise_muscle_targets=[
            item for item in sample_input.exercise_muscle_targets if item.exercise_id != 1
        ],
    )
    app = open_muscle_distribution(schedule_data, unmapped, sets_dataframe)
    assert pd.isna(ranges_table(app).loc["Chest", "Target"])
    assert any("Bench Press" in item.value for item in app.warning)
