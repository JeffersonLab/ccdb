"""CCDB web GUI: a read-only Flask application over a CCDB database.

Two ways to run it:

- `ccdb gui [-p PORT]` builds the app with cerate_ccdb_flask_app() and then sets
  app.config["SQL_CONNECTION_STRING"] from the CLI context.
- `gunicorn ccdbweb:app` imports python/ccdbweb.py, which reads CCDB_CONNECTION (or SQL_CONNECTION_STRING)
  and fails at import when neither is set.

Set CCDB_WEBGUI_PROXY_FIX=1 behind a reverse proxy that forwards under a sub-path; see cerate_ccdb_flask_app().

The database engine is created on the first request (see db.py), so the connection string may be
set after the app exists.
"""
import logging
import os

from flask import Flask
from werkzeug.middleware.proxy_fix import ProxyFix

from ccdb import ccdb_version
from ccdb.webgui import db, errors, views

log = logging.getLogger("ccdb.webgui")


def connection_string_from_env():
    """CCDB_CONNECTION, the CLI's variable, wins over SQL_CONNECTION_STRING, the docker-compose one."""
    return os.getenv("CCDB_CONNECTION") or os.getenv("SQL_CONNECTION_STRING") or ""


def cerate_ccdb_flask_app(connection_string=None, test_config=None):
    """Create and configure an instance of the Flask application.

    :param connection_string: database connection string; the environment is used when it is None.
        An empty value is allowed here and fails with a clear message at the first request.
    :param test_config: mapping merged into app.config, for tests
    """
    app = Flask(__name__, instance_relative_config=True)
    app.config["SQL_CONNECTION_STRING"] = connection_string if connection_string is not None else connection_string_from_env()
    app.config["PROXY_FIX"] = os.getenv("CCDB_WEBGUI_PROXY_FIX", "").lower() in ("1", "true", "yes")
    if test_config:
        app.config.update(test_config)
    if app.config["PROXY_FIX"]:
        # Behind a reverse proxy that sets X-Forwarded-Prefix/Host/Proto, url_for() then builds links
        # under the proxy's prefix (for example /ccdb/) and with the public host and scheme.
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    db.init_app(app)
    views.register(app)
    errors.register(app)

    @app.context_processor
    def template_globals():
        return {"ccdb_version": ccdb_version}
    log.debug("CCDB web GUI app created with %d routes", len(app.url_map._rules))
    return app


# The spelled-right name; the misspelled one stays because the CLI's gui command calls it.
create_ccdb_flask_app = cerate_ccdb_flask_app


if __name__ == '__main__':
    cerate_ccdb_flask_app().run()
