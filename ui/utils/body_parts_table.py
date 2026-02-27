"""
Reusable component: styled body part comparison table.

Mirrors exercise_table.py in structure — same design tokens,
same iframe CSS pattern. Only the columns differ.

Usage:
    from ui.components.body_parts_table import render_body_parts_table
    render_body_parts_table(body_df)

Expected DataFrame columns:
    Body Part, Total_Sets, Sessions, Total_Volume, Avg_1RM
"""

from __future__ import annotations

import pandas as pd
import streamlit.components.v1 as components

from ui.utils.muscle_tags import resolve_muscle_tag


_ROW_HEIGHT_PX    = 52
_HEADER_HEIGHT_PX = 42
_PADDING_PX       = 16

_TABLE_CSS = """
<style>
  :root {
    --bg-base:       #222831;
    --bg-surface:    #393E46;
    --accent:        #00ADB5;
    --accent-dim:    rgba(0, 173, 181, 0.12);
    --accent-border: rgba(0, 173, 181, 0.45);
    --text-primary:  #EEEEEE;
    --text-muted:    #9aa0a6;
    --border:        rgba(255, 255, 255, 0.07);
    --radius-md:     10px;
    --ease:          cubic-bezier(0.4, 0, 0.2, 1);
    --mono:          'Courier New', monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: transparent; font-family: sans-serif; color: var(--text-primary); }

  .table-wrap {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    overflow: hidden;
  }
  table { width: 100%; border-collapse: collapse; }
  thead tr { background: var(--bg-base); border-bottom: 1px solid var(--border); }
  th {
    font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
    color: var(--text-muted); text-transform: uppercase;
    padding: 12px 14px; text-align: left;
  }
  th.right { text-align: right; }
  tbody tr {
    border-bottom: 1px solid var(--border);
    transition: background 0.18s var(--ease);
    animation: fadeIn 0.35s ease both;
  }
  tbody tr:last-child { border-bottom: none; }
  tbody tr:hover { background: rgba(0, 173, 181, 0.05); }
  @keyframes fadeIn { from { opacity:0; transform:translateY(4px); } to { opacity:1; transform:none; } }
  td { padding: 12px 14px; font-size: 13px; vertical-align: middle; }

  .bp-cell { min-width: 130px; }
  .num-cell { font-family: var(--mono); font-size: 13px; text-align: right; color: var(--text-primary); }

  .muscle-tag {
    display: inline-block; font-size: 9px; font-family: var(--mono);
    padding: 2px 7px; border-radius: 4px; letter-spacing: 0.9px;
    text-transform: uppercase; font-weight: 600;
  }
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

  .vol-cell { min-width: 150px; }
  .vol-num  { font-family: var(--mono); font-size: 12px; text-align: right; margin-bottom: 5px; color: var(--text-primary); }
  .bar-track { height: 3px; background: rgba(255,255,255,0.07); border-radius: 2px; overflow: hidden; }
  .bar-fill  { height: 100%; border-radius: 2px; background: linear-gradient(90deg, rgba(0,173,181,0.6), var(--accent)); }

  .rm-cell { min-width: 120px; }
  .rm-val  { font-family: var(--mono); font-size: 13px; font-weight: 700; margin-bottom: 5px; color: var(--accent); }
  .rm-bar-fill { height: 100%; border-radius: 2px; background: linear-gradient(90deg, rgba(255,107,107,0.7), #ffc947); }
</style>
"""

def _vol_bar(vol: float, max_vol: float) -> str:
    pct = round(vol / max_vol * 100, 1) if max_vol else 0
    return (
        f'<div class="vol-num">{int(vol):,}</div>'
        f'<div class="bar-track"><div class="bar-fill" style="width:{pct}%"></div></div>'
    )

def _rm_bar(rm: float, max_rm: float) -> str:
    pct = round(rm / max_rm * 100, 1) if max_rm else 0
    return (
        f'<div class="rm-val">{rm:.1f} kg</div>'
        f'<div class="bar-track"><div class="rm-bar-fill" style="width:{pct}%"></div></div>'
    )

def _bp_cell(body_part: str) -> str:
    tag_label, tag_cls = resolve_muscle_tag(body_part)
    return f'<span class="muscle-tag tag-{tag_cls}">{tag_label}</span>'

def render_body_parts_table(body_df: pd.DataFrame) -> None:
    """
    Render the styled body part comparison table inside a Streamlit page.

    Parameters
    ----------
    body_df : DataFrame with columns:
        Body Part, Total_Sets, Sessions, Total_Volume, Avg_1RM
    """
    max_vol = body_df["Total_Volume"].max()
    max_rm  = body_df["Avg_1RM"].max()

    rows_html = ""
    for i, (_, row) in enumerate(body_df.iterrows()):
        rows_html += f"""
        <tr style="animation-delay:{i * 40}ms">
          <td class="bp-cell">{_bp_cell(row["Body Part"])}</td>
          <td class="num-cell">{int(row["Total_Sets"])}</td>
          <td class="num-cell">{int(row["Sessions"])}</td>
          <td class="vol-cell">{_vol_bar(row["Total_Volume"], max_vol)}</td>
          <td class="rm-cell">{_rm_bar(row["Avg_1RM"], max_rm)}</td>
        </tr>
        """

    html = f"""
    {_TABLE_CSS}
    <div class="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Body Part</th>
            <th class="right">Total Sets</th>
            <th class="right">Sessions</th>
            <th class="right" style="min-width:150px">Total Volume</th>
            <th class="right" style="min-width:120px">Avg 1RM</th>
          </tr>
        </thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """

    height = _HEADER_HEIGHT_PX + len(body_df) * _ROW_HEIGHT_PX + _PADDING_PX
    components.html(html, height=height, scrolling=False)
  