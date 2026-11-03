"""Database access of the HTTP API: one SQLAlchemy engine per process, one session per request.

The engine is created on the first request, so a server that forks workers after importing the app gives each
worker its own pool. The schema version check runs once, when the engine is created; a database that is down
or of the wrong version at that moment is tried again on the next request. Sessions come from a plain
sessionmaker, not a scoped_session: FastAPI may run a request's dependency and its endpoint on different threads
of its pool, so a thread-local registry would hand them different sessions.
"""
import logging
import os
import threading

import sqlalchemy
from sqlalchemy.orm import sessionmaker

from ccdb import AlchemyProvider
from ccdb.webgui.db import normalize_dialect, POOL_RECYCLE_SECONDS

log = logging.getLogger("ccdb.api")

NO_CONNECTION_MESSAGE = ("The CCDB HTTP API has no database connection string. Set CCDB_CONNECTION to something "
                         "like mysql://ccdb_user@hallddb.jlab.org/ccdb or sqlite:////path/to/ccdb.sqlite, or run "
                         "'ccdb -c <connection> api'")


class Database:
    """The engine and the session factory of one API application"""

    def __init__(self, connection_string):
        self.connection_string = connection_string
        self.engine = None
        self.sessions = None
        self._lock = threading.Lock()

    def ensure_engine(self):
        """Creates the engine on first use, after the schema check passed"""
        with self._lock:
            if self.engine is None:
                engine = sqlalchemy.create_engine(normalize_dialect(self.connection_string), pool_pre_ping=True,
                                                  pool_recycle=POOL_RECYCLE_SECONDS)
                sessions = sessionmaker(bind=engine)
                session = sessions()
                try:
                    AlchemyProvider().attach(engine, session)       # runs the schema version check once
                except Exception:
                    session.close()
                    engine.dispose()
                    raise
                session.close()
                self.engine, self.sessions = engine, sessions
                log.info("CCDB HTTP API connected to %s", engine.url.render_as_string(hide_password=True))
        return self.engine

    def provider(self):
        """A provider with a session of its own, for one request; close its session when the request ends"""
        self.ensure_engine()
        provider = AlchemyProvider()
        provider.attach(self.engine, self.sessions(), check_version=False)
        return provider

    def dispose(self):
        if self.engine is not None:
            self.engine.dispose()
            self.engine, self.sessions = None, None


def connection_from_environment():
    """CCDB_CONNECTION, then CCDB_API_CONNECTION; raises RuntimeError with a usage message when neither is set"""
    value = os.environ.get("CCDB_CONNECTION") or os.environ.get("CCDB_API_CONNECTION")
    if not value:
        raise RuntimeError(NO_CONNECTION_MESSAGE)
    return value
