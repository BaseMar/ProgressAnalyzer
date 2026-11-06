"""Copy directly in the browser without a Python rerun or network request."""
import streamlit.components.v2 as components


_COPY = components.component(
    'copy_workout',
    html='''<button type="button">Kopiuj trening</button>
<span role="status" aria-live="polite"></span>
<textarea hidden readonly aria-label="Trening do skopiowania"></textarea>''',
    css='''
button { width: 100%; min-height: 44px; border-radius: 8px; padding: 10px 16px;
    background: #00adb5; color: #111820; border: 1px solid #00adb5;
    font: 600 15px sans-serif; cursor: pointer; }
button:hover { background: #26bec5; }
button:focus-visible { outline: 3px solid #eeeeee; outline-offset: 2px; }
[role="status"] { display: block; font: 13px sans-serif; color: #a9b5bf; margin-top: 6px; }
[role="status"]:empty { display: none; }
textarea { width: 100%; min-height: 180px; box-sizing: border-box; margin-top: 8px;
    background: #222831; color: #eeeeee; font-size: 16px; }
''',
    js='''export default function(component) {
    const {data, parentElement} = component;
    const button = parentElement.querySelector('button');
    const status = parentElement.querySelector('[role="status"]');
    const fallback = parentElement.querySelector('textarea');
    const text = data.text;
    button.textContent = 'Kopiuj trening';
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
            button.textContent = 'Skopiowano ✓';
            status.textContent = 'Otwórz Samsung Notes i wklej trening.';
            fallback.hidden = true;
        } else {
            status.textContent = 'Przytrzymaj tekst poniżej, wybierz Zaznacz wszystko i Kopiuj.';
            fallback.hidden = false;
            fallback.focus();
            fallback.select();
        }
    };
    return () => { button.onclick = null; };
}''',
)


def copy_workout(text, *, key):
    _COPY(data={'text': text}, key=key)
