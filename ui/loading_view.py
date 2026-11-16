"""Temporary loading screens for startup and navigation; no artificial delays."""

from contextlib import contextmanager
from contextvars import ContextVar
from html import escape

import streamlit as st

_active_screen = ContextVar("active_loading_screen", default=None)


class LoadingScreen:
    def __init__(self, placeholder, title, detail):
        self.placeholder = placeholder
        self.title = title
        self.update(detail)

    def update(self, detail):
        self.placeholder.html(
            '<div class="app-loading-screen" role="status" aria-live="polite" '
            'aria-busy="true" aria-atomic="true">'
            '<div class="app-loading-card">'
            '<div class="app-loading-mark" aria-hidden="true">'
            '<div class="app-loading-barbell">'
            '<span class="app-loading-plate outer-left"></span>'
            '<span class="app-loading-plate inner-left"></span>'
            '<span class="app-loading-plate inner-right"></span>'
            '<span class="app-loading-plate outer-right"></span>'
            "</div></div>"
            '<div class="app-loading-brand">Workout Progress Analyzer</div>'
            f'<div class="app-loading-title">{escape(self.title)}</div>'
            f'<div class="app-loading-detail">{escape(detail)}</div>'
            '<div class="app-loading-track" aria-hidden="true">'
            '<div class="app-loading-bar"></div></div>'
            "</div></div>"
        )


@contextmanager
def loading_screen(title, detail="Preparing your view", *, enabled=True):
    # Keep the same delta position on every rerun, including nested/disabled
    # screens, so old routes are replaced before a slow read begins.
    placeholder = st.empty()
    active = _active_screen.get()
    if active is not None:
        if enabled:
            active.update(detail)
        yield active
        return
    if not enabled:
        yield None
        return
    screen = LoadingScreen(placeholder, title, detail)
    token = _active_screen.set(screen)
    try:
        yield screen
    finally:
        _active_screen.reset(token)
        placeholder.empty()


def update_loading_screen(detail):
    active = _active_screen.get()
    if active is not None:
        active.update(detail)
