from __future__ import annotations

import re
from html import unescape
from dataclasses import dataclass
from typing import Callable
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


ROLE_FACTOR = {
    "primary": 1.0,
    "secondary": 0.5,
    "stabilizer": 0.25,
}


@dataclass(frozen=True)
class MuscleTarget:
    muscle_group: str
    muscle_name: str
    role: str
    set_factor: float
    source_note: str


@dataclass(frozen=True)
class ExerciseResolution:
    category: str
    body_part: str
    targets: list[MuscleTarget]


def resolve_exercise(name: str, allow_web: bool = False) -> ExerciseResolution | None:
    """Resolve likely muscle targets from an exercise name.

    The rules are movement-pattern based and backed by the sources recorded in
    source_note. If no confident pattern is found, return None so the UI can
    avoid adding a misleading mapping.
    """
    normalized = _normalize(name)
    if not normalized:
        return None

    for matcher, resolver in _RULES:
        if matcher(normalized):
            return resolver(normalized)

    if allow_web:
        return _resolve_from_web(name)

    return None


def _normalize(value: str) -> str:
    value = value.lower().replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _has_all(*tokens: str) -> Callable[[str], bool]:
    return lambda value: all(token in value for token in tokens)


def _has_any(*tokens: str) -> Callable[[str], bool]:
    return lambda value: any(token in value for token in tokens)


def _target(
    muscle_group: str,
    muscle_name: str,
    role: str,
    source_note: str,
    set_factor: float | None = None,
) -> MuscleTarget:
    return MuscleTarget(
        muscle_group=muscle_group,
        muscle_name=muscle_name,
        role=role,
        set_factor=float(set_factor if set_factor is not None else ROLE_FACTOR[role]),
        source_note=source_note,
    )


def _resolution(category: str, targets: list[MuscleTarget]) -> ExerciseResolution:
    primary = next((target for target in targets if target.role == "primary"), targets[0])
    return ExerciseResolution(category=category, body_part=primary.muscle_group, targets=targets)


def _row(value: str) -> ExerciseResolution:
    source = "Auto-resolved row pattern: T-bar/row references list back as primary with biceps, rear delts, forearms and spinal stabilizers assisting."
    targets = [
        _target("Back", "Latissimus dorsi, trapezius, rhomboids, teres major", "primary", source),
        _target("Shoulders", "Posterior deltoid", "secondary", source, 0.4),
        _target("Biceps", "Biceps brachii, brachialis", "secondary", source),
        _target("Forearms", "Brachioradialis, wrist flexors", "secondary", source, 0.4),
    ]
    if "chest supported" not in value and "machine" not in value:
        targets.append(_target("Lower Back", "Erector spinae", "stabilizer", source, 0.5))
    return _resolution("Pull", targets)


def _vertical_pull(value: str) -> ExerciseResolution:
    source = "Auto-resolved vertical pull pattern: pull-up/pulldown references list lats and upper back as primary with elbow flexors assisting."
    return _resolution(
        "Pull",
        [
            _target("Back", "Latissimus dorsi, teres major", "primary", source),
            _target("Biceps", "Biceps brachii, brachialis", "secondary", source),
            _target("Forearms", "Brachioradialis, wrist flexors", "secondary", source, 0.4),
            _target("Shoulders", "Posterior deltoid", "stabilizer", source),
        ],
    )


def _press(value: str) -> ExerciseResolution:
    source = "Auto-resolved press pattern: bench/chest press references list chest as primary with anterior delts and triceps assisting."
    return _resolution(
        "Push",
        [
            _target("Chest", "Pectoralis major", "primary", source),
            _target("Shoulders", "Anterior deltoid", "secondary", source),
            _target("Triceps", "Triceps brachii", "secondary", source),
        ],
    )


def _shoulder_press(value: str) -> ExerciseResolution:
    source = "Auto-resolved overhead press pattern: shoulder press references list deltoids as primary with triceps and trunk stabilizers assisting."
    return _resolution(
        "Push",
        [
            _target("Shoulders", "Anterior and lateral deltoid", "primary", source),
            _target("Triceps", "Triceps brachii", "secondary", source),
            _target("Chest", "Pectoralis major, clavicular fibers", "stabilizer", source),
            _target("Abs", "Rectus abdominis", "stabilizer", source),
            _target("Lower Back", "Erector spinae", "stabilizer", source),
        ],
    )


def _rear_delt(value: str) -> ExerciseResolution:
    source = "Auto-resolved rear-delt pattern: rear-delt and face-pull references list posterior delts as primary with upper back and grip assisting."
    return _resolution(
        "Pull",
        [
            _target("Shoulders", "Posterior deltoid, external rotators", "primary", source),
            _target("Back", "Trapezius, rhomboids", "secondary", source),
            _target("Forearms", "Wrist flexors", "stabilizer", source),
        ],
    )


def _lateral_raise(value: str) -> ExerciseResolution:
    source = "Auto-resolved lateral raise pattern: lateral raise references list side delts as primary with trapezius and shoulder stabilizers assisting."
    return _resolution(
        "Push",
        [
            _target("Shoulders", "Lateral deltoid", "primary", source),
            _target("Back", "Trapezius, serratus anterior", "stabilizer", source),
        ],
    )


def _fly(value: str) -> ExerciseResolution:
    source = "Auto-resolved fly pattern: fly/crossover references list pectorals as primary with anterior delts and shoulder stabilizers assisting."
    return _resolution(
        "Push",
        [
            _target("Chest", "Pectoralis major", "primary", source),
            _target("Shoulders", "Anterior deltoid", "secondary", source, 0.4),
            _target("Biceps", "Biceps brachii, short head", "stabilizer", source),
        ],
    )


def _triceps(value: str) -> ExerciseResolution:
    source = "Auto-resolved triceps extension/pushdown pattern: triceps references list triceps brachii as primary with grip and shoulder stabilizers assisting."
    return _resolution(
        "Push",
        [
            _target("Triceps", "Triceps brachii", "primary", source),
            _target("Forearms", "Wrist flexors", "stabilizer", source),
            _target("Shoulders", "Shoulder stabilizers", "stabilizer", source),
        ],
    )


def _curl(value: str) -> ExerciseResolution:
    source = "Auto-resolved curl pattern: curl references list elbow flexors as primary with forearms assisting."
    if "hammer" in value:
        return _resolution(
            "Pull",
            [
                _target("Forearms", "Brachioradialis", "primary", source),
                _target("Biceps", "Biceps brachii, brachialis", "secondary", source, 0.75),
            ],
        )
    return _resolution(
        "Pull",
        [
            _target("Biceps", "Biceps brachii, brachialis", "primary", source),
            _target("Forearms", "Brachioradialis, wrist flexors", "secondary", source, 0.5),
        ],
    )


def _squat_or_leg_press(value: str) -> ExerciseResolution:
    source = "Auto-resolved squat/leg press pattern: squat and leg press references list quads as primary with glutes, calves and trunk stabilizers assisting."
    targets = [
        _target("Legs", "Quadriceps, hamstrings", "primary", source),
        _target("Glutes", "Gluteus maximus", "secondary", source, 0.8),
        _target("Calves", "Gastrocnemius, soleus", "secondary", source, 0.35),
    ]
    if "leg press" not in value and "hack" not in value:
        targets.extend(
            [
                _target("Lower Back", "Erector spinae", "stabilizer", source, 0.5),
                _target("Abs", "Rectus abdominis", "stabilizer", source),
                _target("Obliques", "Internal and external obliques", "stabilizer", source),
            ]
        )
    return _resolution("Legs", targets)


def _hinge(value: str) -> ExerciseResolution:
    source = "Auto-resolved hinge/deadlift pattern: hinge references list hamstrings, glutes and spinal erectors with grip and upper back stabilization."
    return _resolution(
        "Legs",
        [
            _target("Legs", "Hamstrings", "primary", source),
            _target("Glutes", "Gluteus maximus", "primary", source, 0.8),
            _target("Lower Back", "Erector spinae", "stabilizer", source, 0.5),
            _target("Back", "Trapezius, latissimus dorsi", "stabilizer", source, 0.4),
            _target("Forearms", "Grip and wrist flexors", "stabilizer", source),
        ],
    )


def _hip_thrust(value: str) -> ExerciseResolution:
    source = "Auto-resolved hip thrust pattern: hip thrust references list glutes as primary with hamstrings, trunk and spinal erectors assisting."
    return _resolution(
        "Legs",
        [
            _target("Glutes", "Gluteus maximus", "primary", source),
            _target("Legs", "Hamstrings, quadriceps", "secondary", source),
            _target("Lower Back", "Erector spinae", "stabilizer", source),
            _target("Abs", "Rectus abdominis", "stabilizer", source),
            _target("Obliques", "Internal and external obliques", "stabilizer", source),
        ],
    )


def _shrug(value: str) -> ExerciseResolution:
    source = "Auto-resolved shrug pattern: shrug references list trapezius as primary with grip assisting."
    return _resolution(
        "Pull",
        [
            _target("Back", "Trapezius, upper fibers", "primary", source),
            _target("Forearms", "Grip and wrist flexors", "stabilizer", source),
        ],
    )


def _leg_extension(value: str) -> ExerciseResolution:
    return _resolution(
        "Legs",
        [
            _target(
                "Legs",
                "Quadriceps femoris",
                "primary",
                "Auto-resolved leg extension pattern: leg extension references isolate the quadriceps.",
            ),
        ],
    )


def _leg_curl(value: str) -> ExerciseResolution:
    source = "Auto-resolved leg curl pattern: leg curl references list hamstrings as primary with calves assisting."
    return _resolution(
        "Legs",
        [
            _target("Legs", "Hamstrings", "primary", source),
            _target("Calves", "Gastrocnemius", "secondary", source, 0.4),
        ],
    )


def _calf_raise(value: str) -> ExerciseResolution:
    return _resolution(
        "Legs",
        [
            _target(
                "Calves",
                "Gastrocnemius, soleus",
                "primary",
                "Auto-resolved calf raise pattern: calf raise references list gastrocnemius and soleus as primary.",
            ),
        ],
    )


def _abs(value: str) -> ExerciseResolution:
    source = "Auto-resolved core flexion pattern: crunch/raise references list rectus abdominis as primary with obliques assisting."
    return _resolution(
        "Push",
        [
            _target("Abs", "Rectus abdominis", "primary", source),
            _target("Obliques", "Internal and external obliques", "secondary", source),
        ],
    )


_RULES: list[tuple[Callable[[str], bool], Callable[[str], ExerciseResolution]]] = [
    (_has_all("t", "bar", "row"), _row),
    (_has_any("row"), _row),
    (_has_any("shrug"), _shrug),
    (_has_any("pullup", "pull up", "pulldown", "pull down", "chinup", "chin up"), _vertical_pull),
    (_has_any("shoulder press", "military press", "overhead press", "ohp"), _shoulder_press),
    (_has_any("rear delt", "face pull", "reverse pec deck", "pec deck reverse"), _rear_delt),
    (_has_any("lateral raise"), _lateral_raise),
    (_has_any("fly", "crossover", "pec dec", "pec deck"), _fly),
    (_has_any("bench", "chest press", "incline press", "decline press", "flat press", "dumbbell press", "dumbell press", "push up", "dip"), _press),
    (_has_any("curl"), _curl),
    (_has_any("hip thrust", "glute bridge"), _hip_thrust),
    (_has_any("deadlift", "romanian", "rdl", "good morning", "hip hinge"), _hinge),
    (_has_any("leg extension"), _leg_extension),
    (_has_any("leg curl"), _leg_curl),
    (_has_any("triceps", "tricep", "pushdown", "extension", "french press", "skull"), _triceps),
    (_has_any("calf", "calves"), _calf_raise),
    (_has_any("squat", "leg press", "hack", "lunge", "split squat"), _squat_or_leg_press),
    (_has_any("crunch", "sit up", "leg raise", "knee raise", "plank"), _abs),
]


_WEB_GROUP_KEYWORDS = {
    "Back": ["latissimus", "lats", "trapezius", "traps", "rhomboid", "teres major"],
    "Chest": ["pectoralis", "pecs", "chest"],
    "Shoulders": ["deltoid", "delts", "rear delt", "anterior delt", "lateral delt"],
    "Biceps": ["biceps", "brachialis"],
    "Triceps": ["triceps"],
    "Forearms": ["forearm", "brachioradialis", "wrist flexor", "grip"],
    "Lower Back": ["erector spinae", "spinal erector", "lower back"],
    "Glutes": ["glute", "gluteus"],
    "Legs": ["quadriceps", "quad", "hamstring", "adductor"],
    "Calves": ["calf", "calves", "gastrocnemius", "soleus"],
    "Abs": ["rectus abdominis", "abdominals", "abs"],
    "Obliques": ["oblique"],
}


_GROUP_MUSCLE_NAMES = {
    "Back": "Latissimus dorsi, trapezius, rhomboids, teres major",
    "Chest": "Pectoralis major",
    "Shoulders": "Deltoids",
    "Biceps": "Biceps brachii, brachialis",
    "Triceps": "Triceps brachii",
    "Forearms": "Brachioradialis, wrist flexors",
    "Lower Back": "Erector spinae",
    "Glutes": "Gluteus maximus",
    "Legs": "Quadriceps, hamstrings",
    "Calves": "Gastrocnemius, soleus",
    "Abs": "Rectus abdominis",
    "Obliques": "Internal and external obliques",
}


def _resolve_from_web(name: str) -> ExerciseResolution | None:
    try:
        html = _fetch_search_html(f"{name} exercise muscles worked primary secondary")
    except OSError:
        return None

    text = _html_to_text(html)
    scores = {
        group: sum(text.count(keyword) for keyword in keywords)
        for group, keywords in _WEB_GROUP_KEYWORDS.items()
    }
    scores = {group: score for group, score in scores.items() if score > 0}
    if not scores:
        return None

    primary_group, primary_score = max(scores.items(), key=lambda item: item[1])
    if primary_score < 2:
        return None

    source = f"Auto-resolved from web search snippets for '{name}' muscles worked."
    targets = [
        _target(primary_group, _GROUP_MUSCLE_NAMES[primary_group], "primary", source)
    ]
    for group, score in sorted(scores.items(), key=lambda item: item[1], reverse=True):
        if group == primary_group or score < 1:
            continue
        role = "secondary" if score >= 2 else "stabilizer"
        targets.append(_target(group, _GROUP_MUSCLE_NAMES[group], role, source))

    return _resolution(_category_for_group(primary_group), targets[:6])


def _fetch_search_html(query: str) -> str:
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
            )
        },
    )
    with urlopen(request, timeout=6) as response:
        return response.read().decode("utf-8", errors="ignore")


def _html_to_text(html: str) -> str:
    html = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    html = re.sub(r"<style.*?</style>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", unescape(text)).lower()


def _category_for_group(group: str) -> str:
    if group in {"Chest", "Shoulders", "Triceps", "Abs", "Obliques"}:
        return "Push"
    if group in {"Legs", "Glutes", "Calves", "Lower Back"}:
        return "Legs"
    return "Pull"
