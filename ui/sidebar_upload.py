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

        if "uploaded_file_name" not in st.session_state:
            st.session_state.uploaded_file_name = None

        if "exercise_mapping" not in st.session_state:
            st.session_state.exercise_mapping = {}

        file = st.sidebar.file_uploader("Upload .txt workout", type=["txt"])

        # Handle file removal from memory
        if not file:
            if st.session_state.uploaded_file_name is not None:
                st.session_state.uploaded_file_name = None
                st.session_state.adding_exercise = False
                st.session_state.pending_exercise = None
                st.session_state.exercise_mapping = {}
            return

        # Track uploaded file to detect changes
        if file.name != st.session_state.uploaded_file_name:
            st.session_state.uploaded_file_name = file.name
            st.session_state.adding_exercise = False
            st.session_state.pending_exercise = None
            st.session_state.exercise_mapping = {}

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
        """Process and validate parsed exercises before importing."""
        exercises_db = self.dm.load_exercises()

        if exercises_db.empty:
            st.sidebar.error("No exercises in database. Add exercises first.")
            return

        # Create normalized name to exercise mapping
        normalized_map = {}
        original_map = {}
        for row in exercises_db.itertuples():
            norm_name = normalize(row.ExerciseName)
            normalized_map[norm_name] = row.ExerciseID
            original_map[norm_name] = row.ExerciseName

        # Apply user's exercise mappings (from selection dialog)
        for original_name, selected_name in st.session_state.exercise_mapping.items():
            parsed_exercise = next((ex for ex in parsed if ex["name"] == original_name), None)
            if parsed_exercise:
                parsed_exercise["name"] = selected_name

        # Check all exercises and handle missing ones
        missing_exercises = []
        for ex in parsed:
            norm_name = normalize(ex["name"])
            if norm_name not in normalized_map:
                missing_exercises.append(ex["name"])

        if missing_exercises:
            st.session_state.adding_exercise = True
            st.session_state.pending_exercise = missing_exercises[0]
            st.rerun()
            return

        # Validate that we have sets
        if not all(ex["sets"] for ex in parsed):
            st.sidebar.error("Some exercises have no valid sets.")
            return

        # Validate time values
        if start_time is None or end_time is None:
            st.sidebar.warning("Time range not found in file. Importing without time data.")

        # Save session with validated data
        try:
            for ex in parsed:
                norm_name = normalize(ex["name"])
                original_name = original_map[norm_name]
                
                self.dm.add_full_session(
                    session_date=workout_date,
                    notes="Imported",
                    exercise_name=original_name,
                    sets_data=ex["sets"],
                    session_start=start_time,
                    session_end=end_time
                )

            st.sidebar.success("Workout imported successfully!")

            # Clear cache and reset state
            st.cache_data.clear()
            st.session_state.adding_exercise = False
            st.session_state.pending_exercise = None
            st.session_state.uploaded_file_name = None
            st.session_state.exercise_mapping = {}
            st.rerun()
        except Exception as e:
            st.sidebar.error(f"Import failed: {str(e)}")

    def _new_exercise_form(self, suggested_name):
        """Form to handle exercise that doesn't exist in database.
        
        First shows available exercises that might match, then allows creating new one.
        """
        st.sidebar.warning(f"Exercise '{suggested_name}' not found in database")

        exercises_db = self.dm.load_exercises()
        
        # Find similar exercises (simple fuzzy match)
        similar = self._find_similar_exercises(suggested_name, exercises_db)
        
        if similar:
            st.sidebar.info("Did you mean? (showing similar exercises)")
            suggested_names = [row.ExerciseName for row in similar]
            selected_exercise = st.sidebar.selectbox(
                "Select existing exercise:",
                options=suggested_names
            )
            
            if st.sidebar.button("✓ Use selected exercise"):
                # Add mapping and attempt import again
                st.session_state.exercise_mapping[suggested_name] = selected_exercise
                st.session_state.adding_exercise = False
                st.session_state.pending_exercise = None
                st.cache_data.clear()
                st.rerun()
                return
            
            st.sidebar.divider()
            st.sidebar.caption("Or add new exercise below")
        
        # Form to add new exercise
        st.sidebar.subheader("Add new exercise")
        name = st.sidebar.text_input("Exercise name", value=suggested_name, key="new_exercise_name")
        category = st.sidebar.selectbox("Category", ["Push", "Pull", "Legs"], key="exercise_category")
        body = st.sidebar.selectbox(
            "Body Part",
            ["Chest", "Back", "Shoulders", "Biceps", "Triceps", "Legs", "Calves"],
            key="exercise_body"
        )

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("➕ Add exercise"):
                if not name or not name.strip():
                    st.sidebar.error("Exercise name cannot be empty")
                    return
                
                try:
                    self.dm.add_exercise(name.strip(), category, body)
                    st.sidebar.success("Exercise added!")
                    
                    # Clear cache and reset state - will re-attempt import
                    st.cache_data.clear()
                    st.session_state.adding_exercise = False
                    st.session_state.pending_exercise = None
                    st.rerun()
                except Exception as e:
                    st.sidebar.error(f"Failed to add exercise: {str(e)}")
        
        with col2:
            if st.button("❌ Cancel"):
                st.session_state.adding_exercise = False
                st.session_state.pending_exercise = None
                st.session_state.exercise_mapping = {}
                st.rerun()

    def _find_similar_exercises(self, query: str, exercises_df):
        """Find exercises with similar normalized names."""
        query_norm = normalize(query)
        similar = []
        
        for row in exercises_df.itertuples():
            exercise_norm = normalize(row.ExerciseName)
            
            # Check for substring match or high similarity
            if (query_norm in exercise_norm or 
                exercise_norm in query_norm or 
                self._similarity_score(query_norm, exercise_norm) > 0.6):
                similar.append(row)
        
        return similar

    def _similarity_score(self, s1: str, s2: str) -> float:
        """Simple similarity score between two strings (0-1)."""
        if s1 == s2:
            return 1.0
        
        # Count matching characters
        matches = sum(c1 == c2 for c1, c2 in zip(s1, s2))
        max_len = max(len(s1), len(s2))
        
        return matches / max_len if max_len > 0 else 0.0

    def _parse_txt(self, text: str):
        """Parse workout data from text format.
        
        Expected format:
        1. Exercise Name
        5x50 / 4x55 / 3x60
        RIR: 2 / 1 / 0
        """
        exercises = []

        # Regex to capture: number + name, sets line, RIR line
        pattern = r"\d+\.\s(.+?)\n(.+?)\nRIR[:\s]*(.+?)(?:\n|$)"
        matches = re.findall(pattern, text, re.S)

        if not matches:
            return None

        for name, sets_line, rir_line in matches:
            name = name.strip()
            
            if not name:
                continue
            
            sets = [s.strip() for s in sets_line.split("/")]
            rirs = [r.strip() for r in rir_line.split("/")]

            # Ensure same number of sets and RIRs
            if len(sets) != len(rirs):
                st.sidebar.warning(f"Exercise '{name}': set count != RIR count. Skipping.")
                continue

            sets_data = []

            for set_str, rir_str in zip(sets, rirs):
                try:
                    # Parse "reps x weight" format
                    if 'x' not in set_str:
                        st.sidebar.warning(f"Exercise '{name}': Invalid set format '{set_str}'. Expected 'reps x weight'")
                        continue
                    
                    reps_str, weight_str = set_str.split("x", 1)
                    reps = int(reps_str.strip())
                    weight = float(weight_str.strip())
                    rir = int(rir_str.strip())
                    
                    # Basic validation
                    if reps <= 0 or weight < 0 or rir < 0:
                        st.sidebar.warning(f"Exercise '{name}': Negative values not allowed. Set skipped.")
                        continue
                    
                    sets_data.append({
                        "reps": reps,
                        "weight": weight,
                        "rir": rir
                    })
                except ValueError as e:
                    st.sidebar.warning(f"Exercise '{name}': Failed to parse set '{set_str}' - {str(e)}")
                    continue

            if sets_data:  # Only add exercise if it has valid sets
                exercises.append({
                    "name": name,
                    "sets": sets_data
                })

        return exercises if exercises else None

    def _parse_time_range(self, text: str):
        """Parse workout time range from text.
        
        Expected format:
        Godzina: 10:30 - 12:45
        
        Returns:
            tuple: (start_time, end_time) or (None, None) if not found
        """
        match = re.search(r"Godzina:\s*(\d{2}:\d{2})\s*[-–—]\s*(\d{2}:\d{2})", text)

        if not match:
            return None, None

        try:
            start = datetime.strptime(match.group(1), "%H:%M").time()
            end = datetime.strptime(match.group(2), "%H:%M").time()
            return start, end
        except ValueError:
            return None, None
