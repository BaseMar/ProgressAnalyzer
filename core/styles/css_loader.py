from pathlib import Path


def load_css_files(path: str = "core/styles/css") -> str:
    css = ""
    base = Path(path)
    for f in sorted(base.glob("*.css")):
        css += f.read_text(encoding="utf-8") + "\n"
    return f"<style>{css}</style>"
