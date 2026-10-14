"""Database access for the web GUI: one SQLAlchemy engine per process, one session per request.

The engine owns the connection pool. It is created on the first request, not when the app is built,
for two reasons: `ccdb gui` sets the connection string after creating the app, and gunicorn forks
workers after importing the app, and a pool created before the fork would be shared by every worker.
The schema version check runs once, when the engine is created.

Each request gets an AlchemyProvider attached to the shared engine and a session from a
scoped_session registry (`g.db`); the registry removes the session when the app context ends.
"""
import logging

import sqlalchemy
from flask import g, request
from sqlalchemy.orm import scoped_session, sessionmaker

from ccdb import AlchemyProvider

log = logging.getLogger("ccdb.webgui")

EXTENSION_KEY = "ccdb"
NO_CONNECTION_MESSAGE = ("CCDB web GUI has no database connection string. Set CCDB_CONNECTION "
                         "to something like mysql://ccdb_user@hallddb.jlab.org/ccdb "
                         "or sqlite:////path/to/ccdb.sqlite")

# Idle MySQL connections are dropped by the server after `wait_timeout` (8 h by default);
# recycling pooled connections every hour keeps the pool below that, and pre-ping catches the rest.
POOL_RECYCLE_SECONDS = 3600


def normalize_dialect(connection_string):
    """SQLAlchemy's bare `mysql://` means the MySQLdb driver, which CCDB does not install; use pymysql."""
    if connection_string.startswith("mysql://"):
        return "mysql+pymysql://" + connection_string[len("mysql://"):]
    return connection_string


class Database:
    """Engine, session registry and schema check for one Flask app. Lives in app.extensions["ccdb"]."""

    def __init__(self, app):
        self.app = app
        self.engine = None
        self.sessions = None  # scoped_session registry, created together with the engine

    def connection_string(self):
        value = self.app.config.get("CCDB_CONNECTION")
        if not value:
            raise RuntimeError(NO_CONNECTION_MESSAGE)
        return value

    def ensure_engine(self):
        """Creates the engine on first use.

        The engine is stored only after the schema check passed, so a database that is down or
        wrong at the first request is tried again on the next one instead of being cached as broken.
        """
        if self.engine is None:
            url = normalize_dialect(self.connection_string())
            engine = sqlalchemy.create_engine(url, pool_pre_ping=True, pool_recycle=POOL_RECYCLE_SECONDS)
            sessions = scoped_session(sessionmaker(bind=engine))
            try:
                AlchemyProvider().attach(engine, sessions)  # runs the schema version check once
            except Exception:
                sessions.remove()
                engine.dispose()
                raise
            sessions.remove()
            self.engine, self.sessions = engine, sessions
            log.info("CCDB web GUI connected to %s", engine.url.render_as_string(hide_password=True))
        return self.engine

    def provider(self):
        """A provider for the current request, on the shared engine and the request's session."""
        self.ensure_engine()
        provider = AlchemyProvider()
        provider.attach(self.engine, self.sessions, check_version=False)
        return provider

    def release(self):
        """Returns the current request's session (and its pooled connection) to the registry."""
        if self.sessions is not None:
            self.sessions.remove()

    def dispose(self):
        """Closes every pooled connection; for tests and clean shutdowns."""
        self.release()
        if self.engine is not None:
            self.engine.dispose()
            self.engine, self.sessions = None, None


def init_app(app):
    database = Database(app)
    app.extensions[EXTENSION_KEY] = database

    @app.before_request
    def attach_provider():
        if request.endpoint in ("static", "health"):
            return  # static files need no database; the health view handles a dead database itself
        g.db = database.provider()

    @app.teardown_appcontext
    def release_session(exception):
        database.release()

    return database


def get_database(app):
    """The Database of an app, for tests and tools."""
    return app.extensions[EXTENSION_KEY]
