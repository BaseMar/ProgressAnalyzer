from __future__ import annotations

import base64
from io import BytesIO
import json
from html import escape
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image, ImageDraw

from ui.utils.ui_helpers import ACCENT, MUTED, SURFACE, TEXT, chart_label


BODY_IMAGE_PATH = Path(__file__).resolve().parents[1] / "wzorzec" / "human_body.png"
VOLUME_RANGES_PATH = Path(__file__).resolve().parents[2] / "user_settings" / "body_heatmap_ranges.json"

DEFAULT_VOLUME_RANGES = {
    "Chest": {"MEV": 10.0, "Target": 12.0, "MRV": 16.0},
    "Back": {"MEV": 14.0, "Target": 20.0, "MRV": 26.0},
    "Lower Back": {"MEV": 4.0, "Target": 6.0, "MRV": 10.0},
    "Glutes": {"MEV": 8.0, "Target": 12.0, "MRV": 18.0},
    "Legs": {"MEV": 10.0, "Target": 14.0, "MRV": 20.0},
    "Shoulders": {"MEV": 8.0, "Target": 10.0, "MRV": 16.0},
    "Biceps": {"MEV": 6.0, "Target": 8.0, "MRV": 14.0},
    "Triceps": {"MEV": 6.0, "Target": 8.0, "MRV": 14.0},
    "Forearms": {"MEV": 4.0, "Target": 6.0, "MRV": 10.0},
    "Abs": {"MEV": 4.0, "Target": 6.0, "MRV": 12.0},
    "Obliques": {"MEV": 4.0, "Target": 6.0, "MRV": 12.0},
    "Calves": {"MEV": 4.0, "Target": 6.0, "MRV": 12.0},
}

BODY_PART_ORDER = list(DEFAULT_VOLUME_RANGES.keys())

STATUS_META = {
    "under": {"label": "Undertrained", "color": "#3B82F6"},
    "on_target": {"label": "Trained", "color": "#22C55E"},
    "over": {"label": "Overtrained", "color": "#F97316"},
    "no_range": {"label": "No range", "color": MUTED},
}

MUSCLE_GROUP_SEEDS = {
    "Shoulders": [(332, 240), (564, 240), (870, 242), (1099, 241)],
    "Chest": [(402, 262), (494, 262)],
    "Back": [
        (960, 228),
        (1010, 228),
        (924, 260),
        (1046, 260),
        (933, 350),
        (1036, 350),
    ],
    "Lower Back": [
        (969, 425),
        (1001, 425),
        (919, 433),
        (1051, 432),
    ],
    "Glutes": [
        (939, 511),
        (1030, 511),
    ],
    "Biceps": [(321, 326), (576, 326)],
    "Triceps": [(860, 314), (1110, 314)],
    "Forearms": [
        (282, 426),
        (614, 426),
        (264, 539),
        (631, 539),
        (819, 429),
        (1150, 429),
        (839, 439),
        (1130, 439),
        (800, 539),
        (1169, 540),
    ],
    "Abs": [
        (428, 332),
        (468, 332),
        (428, 368),
        (468, 368),
        (428, 405),
        (468, 405),
        (432, 467),
        (465, 466),
    ],
    "Obliques": [
        (383, 377),
        (513, 377),
        (388, 444),
        (508, 444),
        (303, 434),
        (593, 434),
        (448, 538),
    ],
    "Legs": [
        (379, 588),
        (517, 588),
        (418, 569),
        (478, 570),
        (406, 677),
        (491, 677),
        (927, 649),
        (1042, 649),
        (891, 600),
        (1078, 600),
    ],
    "Calves": [
        (384, 769),
        (512, 769),
        (363, 832),
        (400, 815),
        (496, 815),
        (536, 846),
        (387, 973),
        (519, 968),
        (361, 985),
        (897, 794),
        (928, 796),
        (1040, 796),
        (1072, 794),
        (912, 921),
        (1054, 925),
        (882, 972),
        (1084, 973),
    ],
}

EXCLUDED_OVERLAY_REGIONS = {
    "hands": [
        (215, 486, 315, 610),
        (584, 486, 684, 610),
        (748, 486, 850, 610),
        (1106, 486, 1208, 610),
    ],
    "feet": [
        (315, 934, 430, 1034),
        (482, 934, 586, 1034),
        (836, 934, 934, 1034),
        (1032, 934, 1125, 1034),
    ],
}


def render_body_heatmap(body_df: pd.DataFrame, period_weeks: float, period_label: str) -> None:
    """Render editable weekly set ranges and a muscle heatmap for filtered data."""
    chart_label("Weekly Volume Ranges")

    ordered_parts = _ordered_body_parts(body_df["Body Part"].tolist())
    ranges = _render_range_inputs(ordered_parts)
    heatmap_df = _build_heatmap_df(body_df, ordered_parts, ranges, period_weeks)

    chart_label(f"Muscle Heatmap | {period_label}")
    _render_heatmap_html(heatmap_df, period_weeks)


def _ordered_body_parts(parts: Iterable[str]) -> list[str]:
    seen = {str(part).title() for part in parts if part}
    ordered = [part for part in BODY_PART_ORDER if part in seen or part in DEFAULT_VOLUME_RANGES]
    extras = sorted(seen.difference(ordered))
    return ordered + extras


def _render_range_inputs(body_parts: list[str]) -> dict[str, dict[str, float]]:
    saved_ranges = _load_volume_ranges()
    rows = []
    for body_part in body_parts:
        defaults = saved_ranges.get(
            body_part,
            DEFAULT_VOLUME_RANGES.get(
                body_part,
                {"MEV": 6.0, "Target": 8.0, "MRV": 12.0},
            ),
        )
        rows.append(
            {
                "Body Part": body_part,
                "MEV": float(defaults["MEV"]),
                "Target": float(defaults["Target"]),
                "MRV": float(defaults["MRV"]),
            }
        )

    edited = st.data_editor(
        pd.DataFrame(rows),
        hide_index=True,
        width="stretch",
        key="body_heatmap_volume_ranges",
        disabled=["Body Part"],
        column_config={
            "Body Part": st.column_config.TextColumn("Body Part", width="medium"),
            "MEV": st.column_config.NumberColumn(
                "MEV",
                help="Minimum effective weekly sets.",
                min_value=0.0,
                max_value=80.0,
                step=1.0,
                format="%.0f",
                width="small",
            ),
            "Target": st.column_config.NumberColumn(
                "Target",
                help="Target weekly sets.",
                min_value=0.0,
                max_value=80.0,
                step=1.0,
                format="%.0f",
                width="small",
            ),
            "MRV": st.column_config.NumberColumn(
                "MRV",
                help="Maximum recoverable weekly sets.",
                min_value=0.0,
                max_value=80.0,
                step=1.0,
                format="%.0f",
                width="small",
            ),
        },
    )

    ranges = {}
    invalid_ranges = []
    for _, row in edited.iterrows():
        body_part = str(row["Body Part"])
        mev, target, mrv = _ordered_range(row["MEV"], row["Target"], row["MRV"])
        if (mev, target, mrv) != (float(row["MEV"]), float(row["Target"]), float(row["MRV"])):
            invalid_ranges.append(body_part)
        ranges[body_part] = {"MEV": mev, "Target": target, "MRV": mrv}

    if invalid_ranges:
        st.warning(
            "Some volume ranges were inconsistent, so they were ordered as MEV <= Target <= MRV: "
            + ", ".join(invalid_ranges)
        )

    _save_volume_ranges(ranges)
    return ranges


def _load_volume_ranges() -> dict[str, dict[str, float]]:
    if not VOLUME_RANGES_PATH.exists():
        return {}

    try:
        raw_ranges = json.loads(VOLUME_RANGES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}

    if not isinstance(raw_ranges, dict):
        return {}

    ranges = {}
    for body_part, values in raw_ranges.items():
        if not isinstance(values, dict):
            continue
        try:
            mev, target, mrv = _ordered_range(values["MEV"], values["Target"], values["MRV"])
        except (KeyError, TypeError, ValueError):
            continue
        ranges[str(body_part).title()] = {"MEV": mev, "Target": target, "MRV": mrv}

    return ranges


def _save_volume_ranges(ranges: dict[str, dict[str, float]]) -> None:
    payload = {
        body_part: {
            "MEV": float(values["MEV"]),
            "Target": float(values["Target"]),
            "MRV": float(values["MRV"]),
        }
        for body_part, values in ranges.items()
    }

    try:
        VOLUME_RANGES_PATH.parent.mkdir(parents=True, exist_ok=True)
        VOLUME_RANGES_PATH.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
    except OSError as exc:
        st.warning(f"Could not save weekly volume ranges: {exc}")


def _ordered_range(mev: float, target: float, mrv: float) -> tuple[float, float, float]:
    ordered = sorted([_range_value(mev), _range_value(target), _range_value(mrv)])
    return ordered[0], ordered[1], ordered[2]


def _range_value(value: float) -> float:
    if pd.isna(value):
        return 0.0
    return float(value)


def _build_heatmap_df(
    body_df: pd.DataFrame,
    body_parts: list[str],
    ranges: dict[str, dict[str, float]],
    period_weeks: float,
) -> pd.DataFrame:
    source = body_df.copy()
    source["Body Part"] = source["Body Part"].astype(str).str.title()
    source = source.set_index("Body Part")

    rows = []
    safe_weeks = max(float(period_weeks), 1.0)

    for body_part in body_parts:
        trained_sets = float(source.loc[body_part, "Total_Sets"]) if body_part in source.index else 0.0
        body_range = ranges.get(body_part, {"MEV": 0.0, "Target": 0.0, "MRV": 0.0})
        mev = float(body_range.get("MEV", 0.0))
        target = float(body_range.get("Target", 0.0))
        mrv = float(body_range.get("MRV", 0.0))
        sets_per_week = trained_sets / safe_weeks

        rows.append(
            {
                "Body Part": body_part,
                "Total Sets": trained_sets,
                "Sets / Week": sets_per_week,
                "MEV": mev,
                "Target": target,
                "MRV": mrv,
                "Status": _status_from_range(sets_per_week, mev, mrv),
            }
        )

    return pd.DataFrame(rows)


def _status_from_range(sets_per_week: float, mev: float, mrv: float) -> str:
    if mev <= 0 and mrv <= 0:
        return "no_range"
    if sets_per_week < mev:
        return "under"
    if mrv > 0 and sets_per_week > mrv:
        return "over"
    return "on_target"


def _render_heatmap_html(heatmap_df: pd.DataFrame, period_weeks: float) -> None:
    rows_html = "".join(_status_row(row) for _, row in heatmap_df.iterrows())
    legend_html = "".join(
        f'<span class="legend-item"><i style="background:{meta["color"]}"></i>{meta["label"]}</span>'
        for meta in STATUS_META.values()
        if meta["label"] != "No range"
    )
    body_image_src = _body_image_data_uri(BODY_IMAGE_PATH.stat().st_mtime_ns)
    overlay_image_src = _body_overlay_data_uri(
        _overlay_status_signature(heatmap_df),
        BODY_IMAGE_PATH.stat().st_mtime_ns,
    )

    html = f"""
    <style>
      :root {{
        --bg-base: #222831;
        --bg-surface: {SURFACE};
        --text-primary: {TEXT};
        --text-muted: {MUTED};
        --border: rgba(255,255,255,0.07);
        --accent: {ACCENT};
      }}
      * {{ box-sizing: border-box; }}
      body {{
        margin: 0;
        background: transparent;
        color: var(--text-primary);
        font-family: sans-serif;
      }}
      .heatmap-shell {{
        display: grid;
        grid-template-columns: minmax(360px, 1fr) 290px;
        gap: 18px;
        align-items: stretch;
        background: var(--bg-surface);
        border: 1px solid var(--border);
        border-radius: 10px;
        padding: 18px;
      }}
      .figure-wrap {{
        background: transparent;
        border: 1px solid var(--border);
        border-radius: 8px;
        min-height: 520px;
        overflow: hidden;
        display: flex;
        align-items: center;
        justify-content: center;
      }}
      .body-canvas {{
        position: relative;
        width: 100%;
        max-width: 100%;
      }}
      .body-image {{
        width: 100%;
        height: auto;
        display: block;
        object-fit: contain;
      }}
      .body-overlay {{
        position: absolute;
        inset: 0;
        width: 100%;
        height: auto;
        pointer-events: none;
      }}
      .panel {{
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-width: 0;
      }}
      .period {{
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 1.2px;
        text-transform: uppercase;
      }}
      .period strong {{
        color: var(--text-primary);
        font-size: 20px;
        letter-spacing: 0;
        display: block;
        margin-top: 4px;
      }}
      .legend {{
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding-bottom: 3px;
      }}
      .legend-item {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        color: var(--text-muted);
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
      }}
      .legend-item i {{
        display: inline-block;
        width: 10px;
        height: 10px;
        border-radius: 2px;
      }}
      .status-list {{
        display: flex;
        flex-direction: column;
        gap: 7px;
      }}
      .status-row {{
        display: grid;
        grid-template-columns: 14px minmax(72px, 1fr) auto;
        gap: 8px;
        align-items: center;
        padding: 9px 10px;
        background: rgba(34,40,49,0.52);
        border: 1px solid var(--border);
        border-radius: 6px;
      }}
      .dot {{
        width: 10px;
        height: 10px;
        border-radius: 999px;
      }}
      .part {{
        font-size: 13px;
        font-weight: 700;
      }}
      .dose {{
        color: var(--text-muted);
        font-family: 'Courier New', monospace;
        font-size: 12px;
        text-align: right;
      }}
      @media (max-width: 760px) {{
        .heatmap-shell {{ grid-template-columns: 1fr; }}
        .figure-wrap {{ min-height: 430px; }}
      }}
    </style>
    <div class="heatmap-shell">
      <div class="figure-wrap">
        <div class="body-canvas">
          <img class="body-image" src="{body_image_src}" alt="Human body front and back reference">
          <img class="body-overlay" src="{overlay_image_src}" alt="">
        </div>
      </div>
      <aside class="panel">
        <div class="period">Normalized Period<strong>{period_weeks:.1f} weeks</strong></div>
        <div class="legend">{legend_html}</div>
        <div class="status-list">{rows_html}</div>
      </aside>
    </div>
    """

    components.html(html, height=620, scrolling=False)


def _overlay_status_signature(heatmap_df: pd.DataFrame) -> tuple[tuple[str, str], ...]:
    return tuple(
        (str(row["Body Part"]), str(row["Status"]))
        for _, row in heatmap_df.iterrows()
    )


@st.cache_data(show_spinner=False)
def _body_overlay_data_uri(
    status_signature: tuple[tuple[str, str], ...],
    mtime_ns: int,
) -> str:
    fill_mask = _body_fill_mask(mtime_ns)
    height, width = fill_mask.shape
    overlay = np.zeros((height, width, 4), dtype=np.uint8)
    statuses = dict(status_signature)

    for body_part, seeds in MUSCLE_GROUP_SEEDS.items():
        status = statuses.get(body_part, "no_range")
        if status == "no_range":
            continue

        color = _hex_to_rgb(STATUS_META[status]["color"])
        group_mask = _mask_from_seeds(fill_mask, seeds)
        overlay[group_mask, :3] = color
        overlay[group_mask, 3] = 118

    image = Image.fromarray(overlay, mode="RGBA")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


@st.cache_data(show_spinner=False)
def _body_fill_mask(mtime_ns: int) -> np.ndarray:
    pixels = np.array(Image.open(BODY_IMAGE_PATH).convert("RGB"))
    max_channel = pixels.max(axis=2)
    min_channel = pixels.min(axis=2)
    mean_channel = pixels.mean(axis=2)

    fill_mask = (
        (mean_channel > 120)
        & (mean_channel < 235)
        & ((max_channel - min_channel) < 28)
    )
    return fill_mask & ~_excluded_overlay_mask(fill_mask.shape)


def _excluded_overlay_mask(shape: tuple[int, int]) -> np.ndarray:
    height, width = shape
    image = Image.new("1", (width, height), 0)
    draw = ImageDraw.Draw(image)

    for regions in EXCLUDED_OVERLAY_REGIONS.values():
        for box in regions:
            draw.ellipse(box, fill=1)

    return np.array(image, dtype=bool)


def _mask_from_seeds(fill_mask: np.ndarray, seeds: list[tuple[int, int]]) -> np.ndarray:
    height, width = fill_mask.shape
    selected = np.zeros_like(fill_mask, dtype=bool)

    for seed_x, seed_y in seeds:
        if not (0 <= seed_x < width and 0 <= seed_y < height):
            continue
        if selected[seed_y, seed_x] or not fill_mask[seed_y, seed_x]:
            continue

        stack = [(seed_x, seed_y)]
        selected[seed_y, seed_x] = True

        while stack:
            x, y = stack.pop()
            for next_x, next_y in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (
                    0 <= next_x < width
                    and 0 <= next_y < height
                    and fill_mask[next_y, next_x]
                    and not selected[next_y, next_x]
                ):
                    selected[next_y, next_x] = True
                    stack.append((next_x, next_y))

    return selected


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = color.lstrip("#")
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


@st.cache_data(show_spinner=False)
def _body_image_data_uri(mtime_ns: int) -> str:
    image = Image.open(BODY_IMAGE_PATH).convert("RGBA")
    pixels = np.array(image)
    rgb = pixels[:, :, :3]
    near_white = (rgb.min(axis=2) > 245) & ((rgb.max(axis=2) - rgb.min(axis=2)) < 12)
    pixels[near_white, 3] = 0

    buffer = BytesIO()
    Image.fromarray(pixels, mode="RGBA").save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _status_row(row: pd.Series) -> str:
    meta = STATUS_META[row["Status"]]
    return f"""
    <div class="status-row">
      <span class="dot" style="background:{meta["color"]}"></span>
      <span class="part">{escape(str(row["Body Part"]))}</span>
      <span class="dose">{row["Sets / Week"]:.1f} | {row["MEV"]:.0f}-{row["MRV"]:.0f}</span>
    </div>
    """
