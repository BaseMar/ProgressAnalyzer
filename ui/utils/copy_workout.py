"""Copy directly in the browser without a Python rerun or network request."""

import streamlit.components.v2 as components

_COPY = components.component(
    "copy_workout",
    html="""<button type="button">Copy workout</button>
<span role="status" aria-live="polite"></span>
<textarea hidden readonly aria-label="Workout to copy"></textarea>""",
    css="""
button { position: relative; overflow: hidden; width: 100%; min-height: 44px;
    border-radius: 10px; padding: 10px 18px;
    background: linear-gradient(135deg, #25c5cd, #00adb5); color: #122b30;
    border: 1px solid rgba(67, 222, 228, .65);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, .2), 0 3px 10px rgba(0, 173, 181, .14);
    font: 600 14px / 1.3 sans-serif; letter-spacing: .1px; cursor: pointer;
    transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease; }
button::after { content: ''; position: absolute; top: 0; left: 12px; right: 12px;
    height: 1px; background: linear-gradient(90deg, transparent, #00adb5, transparent);
    opacity: 0; pointer-events: none; transition: opacity .18s ease; }
@media (hover: hover) {
    button:hover { border-color: #65dce2; transform: translateY(-1px);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, .25), 0 5px 18px rgba(0, 173, 181, .26); }
    button:hover::after { opacity: 1; }
}
button:active { transform: translateY(0) scale(.985); box-shadow: inset 0 2px 5px rgba(0, 0, 0, .16); }
button:focus-visible { outline: 2px solid #00adb5; outline-offset: 3px;
    box-shadow: 0 0 0 4px rgba(0, 173, 181, .12); }
@media (prefers-reduced-motion: reduce) {
    button, button::after { transition: none !important; transform: none !important; }
}
[role="status"] { display: block; font: 13px sans-serif; color: #a9b5bf; margin-top: 6px; }
[role="status"]:empty { display: none; }
textarea { width: 100%; min-height: 180px; box-sizing: border-box; margin-top: 8px;
    background: #222831; color: #eeeeee; font-size: 16px; }
""",
    js="""export default function(component) {
    const {data, parentElement} = component;
    const button = parentElement.querySelector('button');
    const status = parentElement.querySelector('[role="status"]');
    const fallback = parentElement.querySelector('textarea');
    const text = data.text;
    button.textContent = 'Copy workout';
    status.textContent = '';
    fallback.hidden = true;
    fallback.value = text;
    function legacyCopy() {
        const previous = document.activeElement;
        const input = document.createElement('textarea');
        input.value = text;
        input.style.cssText = 'position:fixed;left:-9999px;top:0;font-size:16px;';
        input.setAttribute('readonly', '');
        document.body.appendChild(input);
        let copied = false;
        try {
            input.focus({preventScroll: true});
            input.select();
            input.setSelectionRange(0, text.length);
            copied = document.execCommand('copy');
        } finally {
            input.remove();
            previous?.focus({preventScroll: true});
        }
        return copied;
    }
    button.onclick = async () => {
        let copied = false;
        try {
            if (navigator.clipboard?.writeText) {
                await navigator.clipboard.writeText(text);
                copied = true;
            }
        } catch (_) { /* Browser policy can require the selection fallback. */ }
        if (!copied) {
            try { copied = legacyCopy(); } catch (_) { copied = false; }
        }
        if (copied) {
            button.textContent = 'Copied ✓';
            status.textContent = 'Open Samsung Notes and paste your workout.';
            fallback.hidden = true;
        } else {
            status.textContent = 'Press and hold the text below, then choose Select all and Copy.';
            fallback.hidden = false;
            fallback.focus();
            fallback.select();
        }
    };
    return () => { button.onclick = null; };
}""",
)


def copy_workout(text, *, key):
    _COPY(data={"text": text}, key=key)
