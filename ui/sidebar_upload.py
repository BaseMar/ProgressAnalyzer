import hashlib
import re
from datetime import datetime

import pandas as pd
import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from data_manager import DataManager
from db.exercise_muscle_resolver import resolve_exercise
from ui.utils.exercise_matcher import normalize
from ui.utils.set_load_inputs import make_set_load, render_load_inputs, render_total_loads


class SidebarUpload:
    """Sidebar module for importing workouts from TXT files."""

    def __init__(self, *, manager=None, sidebar=False):
        self.dm = manager if manager is not None else DataManager()
        self._sidebar = sidebar

    @property
    def ui(self):
        # Old parser-only callers can still provide a sidebar warning sink.
        return st.sidebar if getattr(self, "_sidebar", True) else st

    def render(self):
        self.ui.subheader("Import workout")

        if "adding_exercise" not in st.session_state:
            st.session_state.adding_exercise = False

        if "pending_exercise" not in st.session_state:
            st.session_state.pending_exercise = None

        if "uploaded_file_name" not in st.session_state:
            st.session_state.uploaded_file_name = None

        if "exercise_mapping" not in st.session_state:
            st.session_state.exercise_mapping = {}

        file = self.ui.file_uploader("Upload .txt workout", type=["txt"])

        if not file:
            if st.session_state.uploaded_file_name is not None:
                st.session_state.uploaded_file_name = None
                st.session_state.adding_exercise = False
                st.session_state.pending_exercise = None
                st.session_state.exercise_mapping = {}
            return

        content = file.getvalue().decode("utf-8")
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:12]
        if file.name != st.session_state.uploaded_file_name or digest != st.session_state.get(
            "uploaded_file_digest"
        ):
            st.session_state.uploaded_file_name = file.name
            st.session_state["uploaded_file_digest"] = digest
            st.session_state.adding_exercise = False
            st.session_state.pending_exercise = None
            st.session_state.exercise_mapping = {}

        workout_date = self.ui.date_input("Workout date", value=datetime.today())
        parsed = self._parse_txt(content)
        start_time, end_time = self._parse_time_range(content)
        if not parsed:
            self.ui.error("Could not parse file.")
            return

        if st.session_state.adding_exercise:
            self._new_exercise_form(st.session_state.pending_exercise)
            return

        try:
            parsed = self._review_loads(parsed, workout_date, digest)
        except (ValueError, TypeError) as exc:
            self.ui.error(str(exc))
            return
        except SQLAlchemyError:
            self.ui.error("Load details could not be loaded. Please try again.")
            return
        if self.ui.button("Import workout", icon=":material/upload:"):
            self._process(parsed, workout_date, start_time, end_time)

    def _review_loads(self, parsed, workout_date, scope):
        if not self.dm.set_load_storage_ready():
            self.ui.caption(
                "Load details need database setup. Import will preserve the original kg values."
            )
            return parsed
        output = []
        with self.ui.expander("Review body mass and load types"):
            for index, exercise in enumerate(parsed):
                self.ui.markdown(f"**{exercise['name']}**")
                key = f"import_{scope}_{index}"
                settings = render_load_inputs(self.dm, workout_date, key=key)
                sets = [dict(item) for item in exercise["sets"]]
                if settings[0] != "legacy":
                    frame = pd.DataFrame(
                        {"Set": range(1, len(sets) + 1), "kg": [item["weight"] for item in sets]}
                    )
                    edited = st.data_editor(
                        frame,
                        key=f"{key}_weights",
                        hide_index=True,
                        disabled=["Set"],
                        column_config={
                            "kg": st.column_config.NumberColumn(
                                "Weight (kg)" if settings[0] == "external" else "Additional kg",
                                min_value=0.0,
                                required=True,
                            )
                        },
                    )
                    for item, weight in zip(sets, edited["kg"]):
                        item["weight"] = float(weight)
                        item["load"] = make_set_load(settings, weight)
                    render_total_loads(settings, edited["kg"])
                output.append({**exercise, "sets": sets})
        return output

    def _process(self, parsed, workout_date, start_time, end_time):
        """Process and validate parsed exercises before importing."""
        exercises_db = self.dm.load_exercises()

        if exercises_db.empty:
            self.ui.error("No exercises in database. Add exercises first.")
            return

        normalized_map = {}
        original_map = {}
        for row in exercises_db.itertuples():
            norm_name = normalize(row.exercise_name)
            normalized_map[norm_name] = row.exercise_id
            original_map[norm_name] = row.exercise_name

        for original_name, selected_name in st.session_state.exercise_mapping.items():
            parsed_exercise = next((ex for ex in parsed if ex["name"] == original_name), None)
            if parsed_exercise:
                parsed_exercise["name"] = selected_name

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

        if not all(ex["sets"] for ex in parsed):
            self.ui.error("Some exercises have no valid sets.")
            return

        if start_time is None or end_time is None:
            self.ui.warning("Time range not found in file. Importing without time data.")

        try:
            self.dm.add_workout_session(
                workout_date,
                "Imported",
                [
                    {
                        "name": original_map[normalize(ex["name"])],
                        "exercise_id": normalized_map[normalize(ex["name"])],
                        "sets": ex["sets"],
                    }
                    for ex in parsed
                ],
                start_time,
                end_time,
            )

            self.ui.success("Workout imported successfully!")
            st.session_state["history_workout_notice"] = "Workout imported successfully!"
            st.session_state["history_calendar_month"] = f"{workout_date:%Y-%m}"
            st.session_state["history_month"] = f"{workout_date:%Y-%m}"
            st.session_state[f"history_day_{workout_date:%Y-%m}"] = workout_date
            st.session_state["history_add_workout"] = False

            st.session_state.adding_exercise = False
            st.session_state.pending_exercise = None
            st.session_state.uploaded_file_name = None
            st.session_state.exercise_mapping = {}
            st.rerun()
        except Exception as e:
            self.ui.error(f"Import failed: {str(e)}")

    def _new_exercise_form(self, suggested_name):
        """Form to handle exercise that doesn't exist in database.

        First shows similar exercises, then all exercises from database, then allows creating new one.
        """
        self.ui.warning(f"Exercise '{suggested_name}' not found in database")

        exercises_db = self.dm.load_exercises()

        similar = self._find_similar_exercises(suggested_name, exercises_db)

        if similar:
            self.ui.info("Did you mean? (showing similar exercises)")
            suggested_names = [row.exercise_name for row in similar]
            selected_exercise = self.ui.selectbox(
                "Select existing exercise:", options=suggested_names, key="similar_exercise_select"
            )

            if self.ui.button("Use selected exercise", icon=":material/check:"):
                st.session_state.exercise_mapping[suggested_name] = selected_exercise
                st.session_state.adding_exercise = False
                st.session_state.pending_exercise = None
                st.rerun()
                return

            self.ui.divider()

        self.ui.subheader("Or choose from all exercises")
        all_exercise_names = sorted([row.exercise_name for row in exercises_db.itertuples()])
        selected_exercise_all = self.ui.selectbox(
            "Select exercise from database:", options=all_exercise_names, key="all_exercises_select"
        )

        if self.ui.button("Use this exercise", icon=":material/check:"):
            st.session_state.exercise_mapping[suggested_name] = selected_exercise_all
            st.session_state.adding_exercise = False
            st.session_state.pending_exercise = None
            st.rerun()
            return

        self.ui.divider()
        self.ui.caption("Or add new exercise below")

        self.ui.subheader("Add new exercise")
        name = self.ui.text_input("Exercise name", value=suggested_name, key="new_exercise_name")
        resolution = (
            resolve_exercise(name.strip(), allow_web=False) if name and name.strip() else None
        )
        if resolution:
            target_summary = ", ".join(
                f"{target.muscle_group} ({target.role})" for target in resolution.targets
            )
            self.ui.caption(
                f"Detected: {resolution.category} / {resolution.body_part} | {target_summary}"
            )
        elif name and name.strip():
            self.ui.caption(
                "No local match yet. The app will try an internet lookup when you add it."
            )

        if self.ui.button("Add exercise", icon=":material/add:", width="stretch"):
            if not name or not name.strip():
                self.ui.error("Exercise name cannot be empty")
                return
            try:
                if not self.dm.add_exercise(name.strip()):
                    self.ui.error("Failed to add exercise or detect muscle targets.")
                    return

                self.ui.success("Exercise added!")

                st.session_state.adding_exercise = False
                st.session_state.pending_exercise = None
                st.rerun()
            except Exception as e:
                self.ui.error(f"Failed to add exercise: {str(e)}")

        if self.ui.button("Cancel", icon=":material/close:", width="stretch"):
            st.session_state.adding_exercise = False
            st.session_state.pending_exercise = None
            st.session_state.exercise_mapping = {}
            st.rerun()

    def _find_similar_exercises(self, query: str, exercises_df):
        """Find exercises with similar normalized names."""
        query_norm = normalize(query)
        similar = []

        for row in exercises_df.itertuples():
            exercise_norm = normalize(row.exercise_name)

            if (
                query_norm in exercise_norm
                or exercise_norm in query_norm
                or self._similarity_score(query_norm, exercise_norm) > 0.6
            ):
                similar.append(row)

        return similar

    def _similarity_score(self, s1: str, s2: str) -> float:
        """Simple similarity score between two strings (0-1)."""
        if s1 == s2:
            return 1.0

        matches = sum(c1 == c2 for c1, c2 in zip(s1, s2))
        max_len = max(len(s1), len(s2))

        return matches / max_len if max_len > 0 else 0.0

    def _parse_txt(self, text: str):
        """Parse workout data from a TXT workout log.

        Supported examples:
        1. Bench Press
        10x100 / 8x110 / 6x115
        RIR: 2 / 1 / 0

        1) Bench Press
        Sets: 10 x 100 kg, 8x110, 6x115
        RIR 2/1/0
        """
        text = self._normalize_txt(text)
        blocks = self._extract_exercise_blocks(text)
        exercises = []

        for name, block_lines in blocks:
            sets_data = self._parse_exercise_block(name, block_lines)
            if sets_data:
                exercises.append({"name": name, "sets": sets_data})

        return exercises if exercises else None

    def _normalize_txt(self, text: str) -> str:
        """Normalize common text variants before parsing."""
        return (
            text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .replace("\u00d7", "x")
            .replace("\u2715", "x")
            .replace("\u2013", "-")
            .replace("\u2014", "-")
        )

    def _extract_exercise_blocks(self, text: str) -> list[tuple[str, list[str]]]:
        """Split normalized text into exercise blocks."""
        lines = [line.strip() for line in text.splitlines()]
        header_pattern = re.compile(r"^\s*\d+\s*[\.\)\-]\s*(?P<name>.+?)\s*$")
        blocks = []
        current_name = None
        current_lines = []

        for line in lines:
            header_match = header_pattern.match(line)
            if header_match:
                if current_name:
                    blocks.append((current_name, current_lines))
                current_name, inline_data = self._split_name_and_inline_data(
                    header_match.group("name")
                )
                current_lines = [inline_data] if inline_data else []
                continue

            if current_name:
                current_lines.append(line)

        if current_name:
            blocks.append((current_name, current_lines))

        if blocks:
            return [(name, lines) for name, lines in blocks if name]

        return self._extract_unnumbered_blocks(lines)

    def _extract_unnumbered_blocks(self, lines: list[str]) -> list[tuple[str, list[str]]]:
        """Fallback for logs where exercise names are not numbered."""
        blocks = []
        index = 0

        while index < len(lines):
            line = lines[index].strip()
            next_line = lines[index + 1].strip() if index + 1 < len(lines) else ""
            inline_name, inline_data = self._split_name_and_inline_data(line)

            if inline_name and inline_data and not self._is_metadata_line(line):
                blocks.append((inline_name, [inline_data]))
                index += 1
                continue

            if (
                line
                and not self._is_metadata_line(line)
                and not self._contains_set_token(line)
                and self._contains_set_token(next_line)
            ):
                name = self._clean_exercise_name(line)
                block_lines = []
                index += 1

                while index < len(lines):
                    candidate = lines[index].strip()
                    following = lines[index + 1].strip() if index + 1 < len(lines) else ""
                    if (
                        candidate
                        and not self._is_metadata_line(candidate)
                        and not self._contains_set_token(candidate)
                        and self._contains_set_token(following)
                    ):
                        break
                    block_lines.append(candidate)
                    index += 1

                if name:
                    blocks.append((name, block_lines))
                continue

            index += 1

        return blocks

    def _split_name_and_inline_data(self, line: str) -> tuple[str, str]:
        """Split a line that contains both exercise name and set data."""
        matches = self._work_token_matches(line)
        if not matches:
            return self._clean_exercise_name(line), ""

        first_match = matches[0]
        marker = re.search(
            r"\b(warm[- ]?up|rozgrzewka|working|robocze)\s*:\s*$",
            line[: first_match.start()],
            re.IGNORECASE,
        )
        data_start = marker.start() if marker else first_match.start()
        name = self._clean_exercise_name(line[:data_start])
        if not name:
            return "", line

        return name, line[data_start:].strip()

    def _parse_exercise_block(self, name: str, lines: list[str]) -> list[dict]:
        """Parse one exercise block into set dictionaries."""
        set_tokens = []
        rir_values = []

        for line in lines:
            if not line:
                continue
            if re.match(r"^(?:cel|target|plan)\s*:", line, re.IGNORECASE):
                continue
            # Accept English exports and previously saved Polish notes.
            if re.match(r"^(?:results?|wynik)\s*:", line, re.IGNORECASE):
                for part in line.split(":", 1)[1].split("/"):
                    tokens = self._parse_work_tokens(part)
                    if tokens:
                        set_tokens.extend(tokens)
                    elif re.search(r"_+\s*(?:x|s\b)|\d+\s*x\s*_+", part, re.IGNORECASE):
                        # Keep the RIR position of an unfilled template set.
                        set_tokens.append(None)
            else:
                set_tokens.extend(self._parse_work_tokens(line))
            if self._is_rir_line(line):
                rir_values.extend(self._parse_rir_values(line))

        if not any(token is not None for token in set_tokens):
            self.ui.warning(f"Exercise '{name}': no valid sets found.")
            return []

        if rir_values and len(rir_values) != len(set_tokens):
            self.ui.warning(
                f"Exercise '{name}': set count != RIR count. Missing RIR values will be imported as empty."
            )

        sets_data = []
        for idx, token in enumerate(set_tokens):
            if token is None:
                continue
            reps = token["reps"]
            weight = token["weight"]
            rir = rir_values[idx] if idx < len(rir_values) else None
            duration_seconds = token.get("duration_seconds")

            if reps <= 0 or weight < 0 or (rir is not None and rir < 0):
                self.ui.warning(f"Exercise '{name}': negative values not allowed. Set skipped.")
                continue

            sets_data.append(
                {
                    "reps": reps,
                    "weight": weight,
                    "rir": rir,
                    **({"duration_seconds": duration_seconds} if duration_seconds else {}),
                    **({"is_warmup": token["is_warmup"]} if "is_warmup" in token else {}),
                }
            )

        return sets_data

    def _parse_work_tokens(self, line: str) -> list[dict]:
        """Find weighted or duration-based set tokens in source order."""
        tokens = []
        for match in self._work_token_matches(line):
            try:
                if match.re.pattern == self._duration_colon_pattern().pattern:
                    minutes = int(match.group("minutes"))
                    seconds = int(match.group("seconds"))
                    duration_seconds = minutes * 60 + seconds
                    tokens.append(
                        {
                            "reps": duration_seconds,
                            "weight": 0.0,
                            "duration_seconds": duration_seconds,
                        }
                    )
                elif "duration_seconds" in match.groupdict():
                    duration_seconds = int(match.group("duration_seconds"))
                    tokens.append(
                        {
                            "reps": duration_seconds,
                            "weight": float(
                                (match.groupdict().get("weight") or "0").replace(",", ".")
                            ),
                            "duration_seconds": duration_seconds,
                        }
                    )
                else:
                    tokens.append(
                        {
                            "reps": int(match.group("reps")),
                            "weight": float(match.group("weight").replace(",", ".")),
                        }
                    )
                labels = list(
                    re.finditer(
                        r"\b(warm[- ]?up|rozgrzewka|working|robocze)\s*:",
                        line[: match.start()],
                        re.IGNORECASE,
                    )
                )
                if labels:
                    tokens[-1]["is_warmup"] = labels[-1].group(1).lower() not in (
                        "working",
                        "robocze",
                    )
            except ValueError:
                continue

        return tokens

    def _set_token_matches(self, line: str):
        """Find reps/weight token regex matches in source order."""
        pattern = re.compile(
            r"(?<![\dA-Za-z])(?P<reps>\d{1,3})\s*(?:x|\*)\s*(?P<weight>\d+(?:[\.,]\d+)?)\s*(?:kg)?",
            re.IGNORECASE,
        )
        at_pattern = re.compile(
            r"(?<![\dA-Za-z])(?P<reps>\d{1,3})\s*@\s*(?P<weight>\d+(?:[\.,]\d+)?)\s*(?:kg)?",
            re.IGNORECASE,
        )

        return sorted(
            [*pattern.finditer(line), *at_pattern.finditer(line)],
            key=lambda match: match.start(),
        )

    def _work_token_matches(self, line: str):
        """Find weighted and timed set token regex matches in source order."""
        return sorted(
            [
                *self._set_token_matches(line),
                *self._duration_unit_pattern().finditer(line),
                *self._duration_colon_pattern().finditer(line),
            ],
            key=lambda match: match.start(),
        )

    def _duration_unit_pattern(self):
        return re.compile(
            r"(?<![\dA-Za-z])(?P<duration_seconds>\d{1,4})\s*(?:s|sec|secs|sek|sekund|seconds)\b"
            r"(?:\s*@\s*(?P<weight>\d+(?:[\.,]\d+)?)\s*(?:kg)?)?",
            re.IGNORECASE,
        )

    def _duration_colon_pattern(self):
        return re.compile(
            r"(?<![\d:])(?P<minutes>\d{1,2}):(?P<seconds>[0-5]\d)(?![\d:])",
            re.IGNORECASE,
        )

    def _parse_rir_values(self, line: str) -> list[int | None]:
        """Parse RIR values from a line that contains the RIR label."""
        inline_values = re.findall(
            r"\bRIR\b\s*[:=]?\s*(-?\d+)\b",
            line,
            flags=re.IGNORECASE,
        )
        if len(inline_values) > 1:
            return [int(value) for value in inline_values]

        parts = re.split(r"\bRIR\b", line, maxsplit=1, flags=re.IGNORECASE)
        values = parts[1] if len(parts) > 1 else ""
        return [
            None if value.startswith("_") or value == "?" else int(value)
            for value in re.findall(r"-?\d+|_+|\?", values)
        ]

    def _contains_set_token(self, line: str) -> bool:
        return bool(self._parse_work_tokens(line))

    def _is_rir_line(self, line: str) -> bool:
        return bool(re.search(r"\bRIR\b", line, re.IGNORECASE))

    def _is_metadata_line(self, line: str) -> bool:
        return bool(
            re.match(r"^\s*(time|date|workout|godzina|czas|data|trening)\b", line, re.IGNORECASE)
        )

    def _clean_exercise_name(self, name: str) -> str:
        return re.sub(r"\s+", " ", name).strip(" :-")

    def _parse_time_range(self, text: str):
        """Parse workout time range from text.

        Expected format:
        Time: 10:30 - 12:45

        Legacy Polish labels and separators remain accepted on input.

        Returns:
            tuple: (start_time, end_time) or (None, None) if not found
        """
        text = self._normalize_txt(text)
        match = re.search(
            r"(?:\b(?:Time|Godzina|Godz\.?|Czas)\b\s*:?\s*)?(\d{1,2}[:\.]\d{2})\s*(?:-|to|do)\s*(\d{1,2}[:\.]\d{2})",
            text,
            re.IGNORECASE,
        )

        if not match:
            return None, None

        try:
            start = datetime.strptime(self._pad_time(match.group(1)), "%H:%M").time()
            end = datetime.strptime(self._pad_time(match.group(2)), "%H:%M").time()
            return start, end
        except ValueError:
            return None, None

    def _pad_time(self, value: str) -> str:
        value = value.replace(".", ":")
        hour, minute = value.split(":", 1)
        return f"{int(hour):02d}:{minute}"
