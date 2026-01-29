import re
from datetime import datetime
import streamlit as st

from data_manager import DataManager
from ui.utils.exercise_matcher import normalize


class SidebarUpload:
    """Sidebar module for importing workouts from TXT files."""

    def __init__(self):
        self.dm = DataManager()

    def render(self):
        st.sidebar.subheader("Import workout")

        # ---- session state init ----
        if "adding_exercise" not in st.session_state:
            st.session_state.adding_exercise = False

        if "pending_exercise" not in st.session_state:
            st.session_state.pending_exercise = None

        file = st.sidebar.file_uploader("Upload .txt workout", type=["txt"])

        if not file:
            return

        content = file.read().decode("utf-8")
        workout_date = st.sidebar.date_input("Workout date", value=datetime.today())
        parsed = self._parse_txt(content)
        start_time, end_time = self._parse_time_range(content)
        if not parsed:
            st.sidebar.error("Could not parse file.")
            return

        # ---- show add exercise form if needed ----
        if st.session_state.adding_exercise:
            self._new_exercise_form(st.session_state.pending_exercise)
            return

        # ---- IMPORT BUTTON ----
        if st.sidebar.button("Import workout", icon=":material/upload:"):
            self._process(parsed, workout_date, start_time, end_time)

    def _process(self, parsed, workout_date, start_time, end_time):
        exercises_db = self.dm.load_exercises()

        # map normalized names
        name_map = {normalize(row.ExerciseName): row.ExerciseID for row in exercises_db.itertuples()}

        # ---- check missing exercises ----
        for ex in parsed:
            norm_name = normalize(ex["name"])

            if norm_name not in name_map:
                st.session_state.adding_exercise = True
                st.session_state.pending_exercise = ex["name"]
                return

        # ---- save session ----
        for ex in parsed:
            self.dm.add_full_session(
                session_date=workout_date,
                notes="Imported",
                exercise_name=ex["name"],
                sets_data=ex["sets"],
                session_start=start_time,
                session_end=end_time
            )

        st.sidebar.success("Workout imported successfully!")

        st.cache_data.clear()
        st.rerun()

    def _new_exercise_form(self, suggested_name):
        st.sidebar.warning("New exercise detected")

        name = st.sidebar.text_input("Exercise name", value=suggested_name)
        category = st.sidebar.selectbox("Category", ["Push", "Pull", "Legs"])
        body = st.sidebar.selectbox("Body Part",["Chest", "Back", "Shoulders", "Biceps", "Triceps","Legs", "Calves"])

        if st.sidebar.button("Add exercise"):
            self.dm.add_exercise(name, category, body)

            # reset state
            st.session_state.adding_exercise = False
            st.session_state.pending_exercise = None

            st.sidebar.success("Exercise added! Click Import again.")

    def _parse_txt(self, text: str):
        exercises = []

        # Regex to capture: number + name, sets line, RIR line
        pattern = r"\d+\.\s(.+?)\n(.+?)\nRIR[:\s]*(.+?)(?:\n|$)"
        matches = re.findall(pattern, text, re.S)

        for name, sets_line, rir_line in matches:
            sets = [s.strip() for s in sets_line.split("/")]
            rirs = [r.strip() for r in rir_line.split("/")]

            sets_data = []

            for s, r in zip(sets, rirs):
                try:
                    reps_str, weight_str = s.split("x")
                    reps = int(reps_str.strip())
                    weight = float(weight_str.strip())
                    rir = int(r.strip())
                except ValueError:
                    # Skip malformed set
                    continue

                sets_data.append({
                    "reps": reps,
                    "weight": weight,
                    "rir": rir
                })

            exercises.append({
                "name": name.strip(),
                "sets": sets_data
            })

        return exercises

    def _parse_time_range(self, text: str):
        match = re.search(r"Godzina:\s*(\d{2}:\d{2})\s*[-–—]\s*(\d{2}:\d{2})",text)

        if not match:
            return None, None

        start = datetime.strptime(match.group(1), "%H:%M").time()
        end = datetime.strptime(match.group(2), "%H:%M").time()

        return start, end
