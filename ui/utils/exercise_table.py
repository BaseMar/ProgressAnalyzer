from __future__ import annotations

import pandas as pd
import streamlit.components.v1 as components

from ui.utils.muscle_tags import resolve_muscle_tag

# Design tokens (mirrors main.css)
_CSS = """
<style>
  :root {
    --bg-base:       #222831;
    --bg-surface:    #393E46;
    --accent:        #00ADB5;
    --accent-dim:    rgba(0, 173, 181, 0.12);
    --accent-border: rgba(0, 173, 181, 0.45);
    --accent-glow:   rgba(0, 173, 181, 0.20);
    --text-primary:  #EEEEEE;
    --text-muted:    #9aa0a6;
    --border:        rgba(255, 255, 255, 0.07);
    --border-hover:  rgba(0, 173, 181, 0.55);
    --radius-md:     10px;
    --ease:          cubic-bezier(0.4, 0, 0.2, 1);
    --mono:          'Courier New', monospace;
  }

  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; font-family: sans-serif; color: var(--text-primary); }

  /* ── Table wrapper ── */
  .table-wrap {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  table { width: 100%; border-collapse: collapse; }

  /* ── Header ── */
  thead tr {
    background: var(--bg-base);
    border-bottom: 1px solid var(--border);
  }
  th {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.2px;
    color: var(--text-muted);
    text-transform: uppercase;
    padding: 12px 14px;
    text-align: left;
  }
  th.right { text-align: right; }
  th.center { text-align: center; }

  /* ── Body rows ── */
  tbody tr {
    border-bottom: 1px solid var(--border);
    transition: background 0.18s var(--ease), border-color 0.18s var(--ease);
    animation: fadeIn 0.35s ease both;
  }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:hover {
    background: rgba(0, 173, 181, 0.05);
    border-color: rgba(0, 173, 181, 0.12);
  }

  /* Selected row — matches _highlight_selected in original code */
  tbody tr.selected-row {
    background: rgba(0, 173, 181, 0.08);
    border-left: 2px solid var(--accent);
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(4px); }
    to   { opacity: 1; transform: none; }
  }

  td { padding: 12px 14px; font-size: 13px; vertical-align: middle; }

  /* ── Exercise cell ── */
  .exercise-cell { min-width: 180px; }
  .exercise-name {
    font-weight: 500;
    color: var(--text-primary);
    margin-bottom: 5px;
    letter-spacing: 0.1px;
  }

  /* ── Muscle tags — tinted accent variants ── */
  .muscle-tag {
    display: inline-block;
    font-size: 9px;
    font-family: var(--mono);
    padding: 2px 7px;
    border-radius: 4px;
    letter-spacing: 0.9px;
    text-transform: uppercase;
    font-weight: 600;
  }
  /* Each tag uses a hue shift from the base accent #00ADB5 */
  .tag-legs      { background: rgba(0,173,181,0.12);  color: #00ADB5; border: 1px solid rgba(0,173,181,0.30); }
  .tag-back      { background: rgba(0,173,181,0.08);  color: #4ecdc4; border: 1px solid rgba(78,205,196,0.25); }
  .tag-chest     { background: rgba(255,107,107,0.10);color: #ff8585; border: 1px solid rgba(255,107,107,0.25); }
  .tag-calves    { background: rgba(154,160,166,0.10);color: #b0b8bf; border: 1px solid rgba(154,160,166,0.25); }
  .tag-shoulders { background: rgba(255,201,71,0.10); color: #ffc947; border: 1px solid rgba(255,201,71,0.25); }
  .tag-biceps    { background: rgba(0,200,150,0.10);  color: #00c896; border: 1px solid rgba(0,200,150,0.25); }
  .tag-triceps   { background: rgba(200,130,255,0.10);color: #c882ff; border: 1px solid rgba(200,130,255,0.25); }
  .tag-core      { background: rgba(255,160,80,0.10); color: #ffa050; border: 1px solid rgba(255,160,80,0.25); }
  .tag-glutes    { background: rgba(100,180,255,0.10);color: #64b4ff; border: 1px solid rgba(100,180,255,0.25); }
  .tag-other     { background: rgba(255,255,255,0.05);color: var(--text-muted); border: 1px solid var(--border); }

  /* ── Numeric cells ── */
  .num-cell {
    font-family: var(--mono);
    font-size: 13px;
    text-align: right;
    color: var(--text-primary);
  }

  /* ── Volume bar cell ── */
  .vol-cell { min-width: 150px; }
  .vol-num {
    font-family: var(--mono);
    font-size: 12px;
    text-align: right;
    margin-bottom: 5px;
    color: var(--text-primary);
  }
  .bar-track {
    height: 3px;
    background: rgba(255,255,255,0.07);
    border-radius: 2px;
    overflow: hidden;
  }
  .bar-fill {
    height: 100%;
    border-radius: 2px;
    background: linear-gradient(90deg, rgba(0,173,181,0.6), var(--accent));
  }

  /* ── 1RM cell ── */
  .rm-cell { min-width: 110px; }
  .rm-val {
    font-family: var(--mono);
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 5px;
  }
  .rm-bar-fill {
    height: 100%;
    border-radius: 2px;
    background: linear-gradient(90deg, rgba(255,107,107,0.7), #ffc947);
  }

  /* ── RIR dots ── */
  .rir-cell { text-align: center; width: 90px; }
  .rir-dots { display: flex; gap: 3px; justify-content: center; margin-bottom: 3px; }
  .dot {
    width: 7px; height: 7px;
    border-radius: 50%;
    background: rgba(255,255,255,0.07);
    border: 1px solid rgba(255,255,255,0.10);
  }
  .dot.high   { background: var(--accent); border-color: var(--accent-border); }
  .dot.mid    { background: #ffc947; border-color: rgba(255,201,71,0.5); }
  .dot.low    { background: #ff8585; border-color: rgba(255,107,107,0.5); }
  .rir-label  { font-family: var(--mono); font-size: 10px; color: var(--text-muted); }
</style>
"""

_ROW_HEIGHT_PX   = 52
_HEADER_HEIGHT_PX = 42
_PADDING_PX       = 16


# ── Cell builders ─────────────────────────────────────────────────────────────

def _vol_bar(vol: float, max_vol: float) -> str:
    pct = round(vol / max_vol * 100, 1) if max_vol else 0
    return (
        f'<div class="vol-num">{int(vol):,}</div>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
    )


def _rm_bar(rm: float, max_rm: float) -> str:
    pct = round(rm / max_rm * 100, 1) if max_rm else 0
    # Colour tiers using app's own accent / warning palette
    if rm >= max_rm * 0.75:
        color = "var(--accent)"
    elif rm >= max_rm * 0.5:
        color = "#ffc947"
    else:
        color = "#ff8585"
    return (
        f'<div class="rm-val" style="color:{color}">{rm:.1f} kg</div>'
        f'<div class="bar-track"><div class="rm-bar-fill" style="width:{pct}%"></div></div>'
    )


def _rir_dots(rir: float) -> str:
    if rir <= 1.5:
        cls, filled = "high", 3 if rir <= 1.3 else 2
    elif rir <= 1.9:
        cls, filled = "mid", 2
    else:
        cls, filled = "low", 1
    dots = "".join(
        f'<span class="dot {cls if i < filled else ""}"></span>'
        for i in range(3)
    )
    return f'<div class="rir-dots">{dots}</div><div class="rir-label">{rir:.1f}</div>'


def _exercise_cell(name: str, body_part: str | None) -> str:
    tag_label, tag_cls = resolve_muscle_tag(body_part)
    return (
        f'<div class="exercise-name">{name}</div>'
        f'<span class="muscle-tag tag-{tag_cls}">{tag_label}</span>'
    )


# ── Public component ──────────────────────────────────────────────────────────

def render_exercise_table(compare_df: pd.DataFrame, selected: str) -> None:
    """
    Render the styled exercise comparison table inside a Streamlit page.

    Parameters
    ----------
    compare_df : DataFrame with columns:
        Exercise, Total Sets, Sessions, Total Volume,
        Est. 1RM, Avg RIR, Avg Sets / Session, body_part
    selected : name of the currently selected exercise (highlighted row)
    """
    max_vol = compare_df["Total Volume"].max()
    max_rm  = compare_df["Est. 1RM"].max()

    rows_html = ""
    for i, (_, row) in enumerate(compare_df.iterrows()):
        row_class = "selected-row" if row["Exercise"] == selected else ""
        delay = f"animation-delay:{i * 40}ms"
        rows_html += f"""
        <tr class="{row_class}" style="{delay}">
          <td class="exercise-cell">{_exercise_cell(row["Exercise"], row.get("body_part"))}</td>
          <td class="num-cell">{int(row["Total Sets"])}</td>
          <td class="num-cell">{int(row["Sessions"])}</td>
          <td class="vol-cell">{_vol_bar(row["Total Volume"], max_vol)}</td>
          <td class="rm-cell">{_rm_bar(row["Est. 1RM"], max_rm)}</td>
          <td class="rir-cell">{_rir_dots(row["Avg RIR"])}</td>
          <td class="num-cell">{row["Avg Sets / Session"]:.1f}</td>
        </tr>
        """

    html = f"""
    {_CSS}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Exercise</th>
            <th class="right">Sets</th>
            <th class="right">Sessions</th>
            <th class="right" style="min-width:150px">Total Volume</th>
            <th class="right" style="min-width:110px">Est. 1RM</th>
            <th class="center">Avg RIR</th>
            <th class="right">Sets / Session</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """

    height = _HEADER_HEIGHT_PX + len(compare_df) * _ROW_HEIGHT_PX + _PADDING_PX
    components.html(html, height=height, scrolling=False)
    