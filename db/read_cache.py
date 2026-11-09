"""Share read results within one render, never across users or Streamlit reruns."""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from threading import Lock
from weakref import WeakSet

from sqlalchemy import event, inspect
from sqlalchemy.engine import Connection, Engine


_current = ContextVar('render_reads', default=None)
_installed = WeakSet()
_install_lock = Lock()


def _key(value):
    if isinstance(value, Connection):
        return value.engine
    if isinstance(value, dict):
        return frozenset((key, _key(item)) for key, item in value.items())
    if isinstance(value, (set, frozenset)):
        return frozenset(_key(item) for item in value)
    if isinstance(value, (list, tuple)):
        return tuple(_key(item) for item in value)
    return value


class _ReadCache:
    def __init__(self):
        self.values = {}
        self.written = set()


def _before_execute(connection, cursor, statement, parameters, context, executemany):
    cache = _current.get()
    if cache is None:
        return
    # Invalidate before a write so services also see their uncommitted changes.
    # Unknown statements invalidate conservatively, including data-changing CTEs.
    sql = ' '.join(statement.upper().split())
    control = sql in ('BEGIN', 'SET TRANSACTION READ ONLY', 'PRAGMA QUERY_ONLY=ON', 'PRAGMA QUERY_ONLY')
    if not control and not sql.startswith(('SELECT ', 'SHOW ', 'PRAGMA MAIN.', 'PRAGMA TEMP.')):
        cache.values.clear()
        cache.written.add(connection)


def _finish(connection):
    cache = _current.get()
    if cache is not None and connection in cache.written:
        cache.values.clear()
        cache.written.discard(connection)


def install_read_invalidation(engine):
    """Install context-aware listeners once, before publishing a shared engine.

    Listeners have no render/user state. They remain installed to avoid mutating
    SQLAlchemy's listener collections while other threads execute statements.
    Disposable/test engines can also be registered on first scoped read.
    """
    with _install_lock:
        if engine in _installed:
            return
        event.listen(engine, 'before_cursor_execute', _before_execute)
        event.listen(engine, 'commit', _finish)
        event.listen(engine, 'rollback', _finish)
        _installed.add(engine)


@contextmanager
def read_scope():
    """Keep one render's reads together and discard them on every exit path.

    Nested services reuse the active scope. Outside a scope, readers always
    query the database. Successful or attempted writes invalidate scoped reads.
    """
    if _current.get() is not None:
        yield
        return
    cache = _ReadCache()
    token = _current.set(cache)
    try:
        yield
    finally:
        cache.values.clear()
        cache.written.clear()
        _current.reset(token)


def read_cached(function):
    """Memoize a read service whose first argument is an engine or connection.

    Callers treat returned domain objects/collections as read-only. Cached
    values are local to the current read_scope, with no TTL or global state.
    """
    @wraps(function)
    def wrapped(source, *args, **kwargs):
        cache = _current.get()
        # Transaction adapters retain their caller-owned connection semantics.
        if cache is None or not isinstance(source, (Engine, Connection)):
            return function(source, *args, **kwargs)
        install_read_invalidation(source.engine if isinstance(source, Connection) else source)
        key = (function, _key(source), _key(args), _key(kwargs))
        if key not in cache.values:
            cache.values[key] = function(source, *args, **kwargs)
        return cache.values[key]
    return wrapped


@read_cached
def table_names(connection):
    """Inspect the current default schema at most once within a read scope."""
    return frozenset(inspect(connection).get_table_names())


def has_table(connection, name):
    if _current.get() is None:
        return inspect(connection).has_table(name)
    return name in table_names(connection)
