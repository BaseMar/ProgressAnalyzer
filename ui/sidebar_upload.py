import hashlib
import re
from datetime import datetime

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from data_manager import DataManager
from db.exercise_muscle_resolver import resolve_exercise
from ui.utils.exercise_matcher import normalize
from ui.utils.ui_helpers import section_header

PURPOSE_LABEL = re.compile(r"\b(warm[-–— ]?up|rozgrzewka|working|robocze)\s*:", re.IGNORECASE)
RIR_LABEL = re.compile(r"\bRIR\b\s*[:=]?\s*", re.IGNORECASE)


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
        if getattr(self, "_sidebar", True):
            self.ui.subheader("Import workout")
        else:
            section_header("Import workout", first=True)

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
        self._show_preview(parsed)
        if self.ui.button("Import workout", icon=":material/upload:"):
            self._process(parsed, workout_date, start_time, end_time)

    def _review_loads(self, parsed, workout_date, scope):
        resolved = self._resolve_exercises(parsed)
        if not self.dm.set_load_storage_ready():
            self.ui.caption(
                "Load details need database setup. Import will preserve the original kg values."
            )
            return resolved
        prepared = iter(
            self.dm.prepare_load_entries(
                [exercise for exercise in resolved if "exercise_id" in exercise], workout_date
            )
        )
        return [next(prepared) if "exercise_id" in exercise else exercise for exercise in resolved]

    @staticmethod
    def _catalog_candidates(name, catalog):
        exact = [row for row in catalog if row.exercise_name == name]
        if exact:
            return exact
        normalized = " ".join(normalize(name).split())
        if not normalized:
            return []
        return [
            row for row in catalog if " ".join(normalize(row.exercise_name).split()) == normalized
        ]

    def _resolve_exercises(self, parsed):
        catalog = tuple(self.dm.load_exercises().itertuples())
        by_id = {int(row.exercise_id): row for row in catalog}
        mapping = st.session_state.get("exercise_mapping", {})
        resolved = []
        for exercise in parsed:
            name = exercise["name"]
            chosen_id = exercise.get("exercise_id", mapping.get(name))
            row = by_id.get(chosen_id)
            if chosen_id is None:
                candidates = self._catalog_candidates(name, catalog)
                row = candidates[0] if len(candidates) == 1 else None
            if row is None:
                resolved.append({"name": name, "sets": exercise["sets"]})
            else:
                resolved.append(
                    {**exercise, "name": row.exercise_name, "exercise_id": int(row.exercise_id)}
                )
        return resolved

    def _show_preview(self, exercises):
        rows = [
            {
                "Exercise": exercise["name"],
                "Set": index,
                "Reps": "—" if item.get("duration_seconds") else str(item["reps"]),
                "Seconds": str(item["duration_seconds"]) if item.get("duration_seconds") else "—",
                "kg": item["weight"],
                "RIR": "—" if item["rir"] is None else str(item["rir"]),
                "Purpose": {True: "Warm-up", False: "Working"}.get(item.get("is_warmup"), "Auto"),
            }
            for exercise in exercises
            for index, item in enumerate(exercise["sets"], start=1)
        ]
        self.ui.expander("Import preview").table(rows)

    def _process(self, parsed, workout_date, start_time, end_time):
        """Process and validate parsed exercises before importing."""
        resolved = self._resolve_exercises(parsed)
        unresolved = next((ex for ex in resolved if "exercise_id" not in ex), None)
        if unresolved is not None:
            st.session_state.adding_exercise = True
            st.session_state.pending_exercise = unresolved["name"]
            st.rerun()
            return

        if not all(ex["sets"] for ex in resolved):
            self.ui.error("Some exercises have no valid sets.")
            return

        if start_time is None or end_time is None:
            self.ui.warning("Time range not found in file. Importing without time data.")

        try:
            self.dm.add_workout_session(
                workout_date,
                "Imported",
                resolved,
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
        """Resolve an ambiguous or unknown name before importing its sets."""
        exercises_db = self.dm.load_exercises()
        catalog = tuple(exercises_db.itertuples())
        candidates = self._catalog_candidates(suggested_name, catalog)

        if len(candidates) > 1:
            self.ui.warning(f"Exercise '{suggested_name}' matches multiple catalog entries.")
            self._choose_exercise(suggested_name, candidates, "ambiguous", "Use selected exercise")
            self._cancel_exercise_choice()
            return

        self.ui.warning(f"Exercise '{suggested_name}' not found in database")

        similar = self._find_similar_exercises(suggested_name, exercises_db)

        if similar:
            self.ui.info("Did you mean? (showing similar exercises)")
            self._choose_exercise(suggested_name, similar, "similar", "Use selected exercise")
            self.ui.divider()

        if catalog:
            self.ui.subheader("Or choose from all exercises")
            self._choose_exercise(suggested_name, catalog, "all", "Use this exercise")
            self.ui.divider()

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

                saved = self._catalog_candidates(
                    name.strip(), tuple(self.dm.load_exercises().itertuples())
                )
                if len(saved) == 1:
                    self._remember_exercise(suggested_name, int(saved[0].exercise_id))
            except Exception as e:
                self.ui.error(f"Failed to add exercise: {str(e)}")

        self._cancel_exercise_choice()

    def _choose_exercise(self, name, candidates, kind, button_label):
        labels = {int(row.exercise_id): row.exercise_name for row in candidates}
        if len(set(labels.values())) < len(labels):
            labels = {key: f"{label} (#{key})" for key, label in labels.items()}
        selected = self.ui.selectbox(
            "Select exercise from database",
            sorted(labels, key=labels.get),
            format_func=labels.__getitem__,
            index=None,
            key=f"import_exercise_{kind}_{name}",
        )
        if self.ui.button(button_label, icon=":material/check:", disabled=selected is None):
            self._remember_exercise(name, selected)

    def _remember_exercise(self, name, exercise_id):
        st.session_state.exercise_mapping[name] = exercise_id
        st.session_state.adding_exercise = False
        st.session_state.pending_exercise = None
        st.rerun()

    def _cancel_exercise_choice(self):
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
        header_pattern = re.compile(r"^\s*\d+\s*[.)\-–—]\s*(?P<name>.+?)\s*$")
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
            next_line = self._following_work_line(lines, index)
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
                    following = self._following_work_line(lines, index)
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

    def _following_work_line(self, lines, index):
        for line in lines[index + 1 :]:
            line = line.strip()
            if not line or (self._is_metadata_line(line) and not self._contains_set_token(line)):
                continue
            return line
        return ""

    def _split_name_and_inline_data(self, line: str) -> tuple[str, str]:
        """Split a line that contains both exercise name and set data."""
        matches = self._work_token_matches(line)
        if not matches:
            return self._clean_exercise_name(line), ""

        first_match = matches[0]
        prefix = line[: first_match.start()]
        labels = list(PURPOSE_LABEL.finditer(prefix))
        marker = labels[-1] if labels and not prefix[labels[-1].end() :].strip() else None
        data_start = marker.start() if marker else first_match.start()
        result = re.search(r"\b(?:results?|wynik)\s*:\s*$", line[:data_start], re.IGNORECASE)
        if result:
            data_start = result.start()
        name = self._clean_exercise_name(line[:data_start]).removesuffix(":").rstrip()
        if not name:
            return "", line

        return name, line[data_start:].strip()

    def _parse_exercise_block(self, name: str, lines: list[str]) -> list[dict]:
        """Parse one exercise block into set dictionaries."""
        set_tokens = []
        rir_values = []
        inline_rir = {}
        metadata = self._load_metadata(lines)

        for line in lines:
            if not line:
                continue
            if re.match(r"^(?:cel|target|plan)\s*:", line, re.IGNORECASE):
                continue
            result = re.match(r"^(?:results?|wynik)\s*:\s*", line, re.IGNORECASE)
            if result:
                line = line[result.end() :]
            prefix, *suffix = RIR_LABEL.split(line, maxsplit=1)
            inline = bool(suffix)
            if suffix and self._is_rir_list(prefix, suffix[0]):
                rir_values.extend(self._parse_rir_values(suffix[0], name))
                line, inline = prefix, False
            tokens, annotations = self._parse_set_line(
                line, name, result=bool(result), inline=inline
            )
            inline_rir.update(
                {len(set_tokens) + index: value for index, value in annotations.items()}
            )
            set_tokens.extend(tokens)

        if not any(token is not None for token in set_tokens):
            self.ui.warning(f"Exercise '{name}': no valid sets found.")
            return []

        if len(rir_values) > len(set_tokens):
            self.ui.warning(f"Exercise '{name}': excess RIR fields were ignored.")
        elif rir_values and len(rir_values) < len(set_tokens):
            self.ui.warning(
                f"Exercise '{name}': set count != RIR count. Missing RIR values will be imported as empty."
            )

        sets_data = []
        for idx, token in enumerate(set_tokens):
            if token is None:
                continue
            reps = token["reps"]
            weight = token["weight"]
            rir = inline_rir.get(idx, rir_values[idx] if idx < len(rir_values) else None)
            duration_seconds = token.get("duration_seconds")

            if reps <= 0 or weight < 0:
                self.ui.warning(f"Exercise '{name}': negative values not allowed. Set skipped.")
                continue

            sets_data.append(
                {
                    "reps": reps,
                    "weight": weight,
                    "rir": rir,
                    **({"duration_seconds": duration_seconds} if duration_seconds else {}),
                    **({"is_warmup": token["is_warmup"]} if "is_warmup" in token else {}),
                    **metadata,
                    **({"_weight_mode": "additional"} if token.get("additional") else {}),
                }
            )

        return sets_data

    def _is_rir_list(self, prefix, values):
        if not prefix.strip():
            return True
        if RIR_LABEL.search(values):
            return False
        first, *later = values.split("/")
        if any(self._contains_set_token(part) or self._empty_result(part) for part in later):
            return False
        return bool(later or re.fullmatch(r"(?:\d+|_+|\?)(?:[\s,;]+(?:\d+|_+|\?))+", first.strip()))

    @staticmethod
    def _empty_result(part):
        return bool(re.search(r"_+\s*(?:[x×✕]|s\b)|\d+\s*[x×✕]\s*_+", part, re.IGNORECASE))

    def _parse_set_line(self, line, name, *, result, inline):
        parts = line.split("/") if result or inline else [line]
        tokens, annotations = [], {}
        purpose = None
        for part in parts:
            work, *entries = RIR_LABEL.split(part) if inline else (part,)
            for entry in entries:
                # A second annotated set can follow on the same line without a slash.
                next_set = next(
                    (m for m in self._work_token_matches(entry) if entry[: m.start()].strip(" ,;")),
                    None,
                )
                label = PURPOSE_LABEL.search(entry)
                end = min(
                    next_set.start() if next_set else len(entry),
                    label.start() if label else len(entry),
                )
                values = self._parse_rir_values(entry[:end].strip(" ,;"), name)
                count = len(self._work_token_matches(work)) or int(
                    result and self._empty_result(work)
                )
                index = len(tokens) + count - 1
                if not count or index in annotations or len(values) > 1:
                    self.ui.warning(f"Exercise '{name}': excess inline RIR fields were ignored.")
                if count and index not in annotations:
                    annotations[index] = values[0] if values else None
                work += " " + entry[end:]
            parsed = self._parse_work_tokens(work)
            for token in parsed:
                if purpose is not None:
                    token.setdefault("is_warmup", purpose)
            labels = list(PURPOSE_LABEL.finditer(work))
            if labels:
                purpose = labels[-1].group(1).lower() not in ("working", "robocze")
            tokens.extend(parsed or ([None] if result and self._empty_result(work) else []))
        return tokens, annotations

    def _load_metadata(self, lines):
        result = {}
        for line in lines:
            mode = re.match(
                r"^(?:weight|kg)\s*:\s*(additional|body[_ ]mass|total|assistance)\s*$",
                line,
                re.IGNORECASE,
            )
            if mode:
                result["_weight_mode"] = mode.group(1).lower().replace(" ", "_")
            mass = re.match(
                r"^(?:body mass|masa ciała|masa ciala)\s*(?:\(kg\))?\s*:\s*(\d+(?:[.,]\d+)?)",
                line,
                re.IGNORECASE,
            )
            if mass:
                result["_body_mass_kg"] = float(mass.group(1).replace(",", "."))
            assistance = re.match(
                r"^(?:assistance|wspomaganie)\s*(?:\(kg\))?\s*:\s*(\d+(?:[.,]\d+)?)",
                line,
                re.IGNORECASE,
            )
            if assistance:
                result["_assistance_kg"] = float(assistance.group(1).replace(",", "."))
        return result

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
                labels = list(PURPOSE_LABEL.finditer(line[: match.start()]))
                if match.groupdict().get("additional"):
                    tokens[-1]["additional"] = True
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
            r"(?<![\dA-Za-z])(?P<reps>\d{1,3})\s*[x*×✕]\s*(?P<additional>\+)?(?P<weight>\d+(?:[\.,]\d+)?)\s*(?:kg)?",
            re.IGNORECASE,
        )
        at_pattern = re.compile(
            r"(?<![\dA-Za-z])(?P<reps>\d{1,3})\s*@\s*(?P<additional>\+)?(?P<weight>\d+(?:[\.,]\d+)?)\s*(?:kg)?",
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
            r"(?:\s*@\s*(?P<additional>\+)?(?P<weight>\d+(?:[\.,]\d+)?)\s*(?:kg)?)?",
            re.IGNORECASE,
        )

    def _duration_colon_pattern(self):
        return re.compile(
            r"(?<![\d:])(?P<minutes>\d{1,2}):(?P<seconds>[0-5]\d)(?![\d:])",
            re.IGNORECASE,
        )

    def _parse_rir_values(self, text: str, name: str) -> list[int | None]:
        """Preserve missing and invalid slots so later effort stays with its set."""
        if "/" in text:
            fields = text.split("/")
        elif "," in text or ";" in text:
            fields = re.split(r"[,;]", text)
        else:
            fields = text.split()
        values = []
        for field in fields:
            field = field.strip()
            if field.isdecimal() and len(field) <= 10 and int(field) <= 2_147_483_647:
                values.append(int(field))
            else:
                values.append(None)
                if field and not re.fullmatch(r"_+|\?", field):
                    self.ui.warning(
                        f"Exercise '{name}': invalid RIR '{field}' was kept as unknown."
                    )
        return values

    def _contains_set_token(self, line: str) -> bool:
        return bool(self._parse_work_tokens(line))

    def _is_metadata_line(self, line: str) -> bool:
        if re.match(
            r"^\s*(weight|kg|body mass|assistance|masa ciała|masa ciala|wspomaganie)\s*(?:\(kg\))?\s*:",
            line,
            re.IGNORECASE,
        ):
            return True
        return bool(
            re.match(r"^\s*(time|date|workout|godzina|czas|data|trening)\b", line, re.IGNORECASE)
        )

    def _clean_exercise_name(self, name: str) -> str:
        return name.strip()

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
