"""The CCDB HTTP API: a read-only FastAPI application over a CCDB database (docs/apis/http.md).

    ccdb -c mysql://ccdb_user@hallddb.jlab.org/ccdb api -p 8000            # a development server
    CCDB_CONNECTION=... uvicorn ccdb.api:app --workers 4                   # a deployment, behind a cache

Every endpoint lives under /api/v1 and only reads. The OpenAPI document is /api/v1/openapi.json, the interactive
page /api/v1/docs. Responses carry cache headers (ccdb.api.responses); a deployment puts a cache in front of the
API (docker/nginx/ccdb-api.conf), which is part of the design, not an option.
"""
import logging

from ccdb import version as ccdb_version_module

API_PREFIX = "/api/v1"

log = logging.getLogger("ccdb.api")


def create_app(connection_string=None):
    """The application for one database; without a connection string, CCDB_CONNECTION is read now"""
    from fastapi import FastAPI, Request
    from sqlalchemy import text

    from . import browse, constants, snapshots
    from .database import Database, connection_from_environment
    from .errors import install_error_handlers
    from .responses import JSON, NO_STORE, SHORT, respond, dump_json

    connection_string = connection_string or connection_from_environment()
    app = FastAPI(title="CCDB HTTP API", version=ccdb_version_module.version,
                  description="Read-only access to the calibration constants of a CCDB database. "
                              "Documentation: https://jeffersonlab.github.io/ccdb/#/apis/http",
                  openapi_url=API_PREFIX + "/openapi.json", docs_url=API_PREFIX + "/docs", redoc_url=None)
    app.state.database = Database(connection_string)
    install_error_handlers(app)

    @app.get(API_PREFIX + "/health", summary="Liveness and database check: 200 or 503, never cached", tags=["service"])
    def health(request: Request):
        try:
            engine = app.state.database.ensure_engine()
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            body, status = {"status": "ok", "database": "ok", "version": ccdb_version_module.version}, 200
        except Exception as error:
            # The driver's message names the host and the user; the route is open, so it gets a fixed string
            log.warning("CCDB HTTP API health check failed: %s", error)
            body, status = {"status": "error", "database": "unavailable", "version": ccdb_version_module.version}, 503
        return respond(request, dump_json(body), JSON, NO_STORE, status_code=status)

    @app.middleware("http")
    async def openapi_cache_headers(request, call_next):
        """FastAPI serves the OpenAPI document itself; it gets the one-minute rule and an ETag like every answer"""
        response = await call_next(request)
        if request.url.path == app.openapi_url:
            import hashlib
            response.headers["Cache-Control"] = SHORT
            response.headers["ETag"] = '"{0}"'.format(hashlib.sha256(dump_json(app.openapi()).encode("utf-8")).hexdigest())
        return response

    app.include_router(browse.router, prefix=API_PREFIX, tags=["browse"])
    app.include_router(constants.router, prefix=API_PREFIX, tags=["constants"])
    app.include_router(snapshots.router, prefix=API_PREFIX, tags=["bundle"])
    return app


def __getattr__(name):
    """`ccdb.api:app` for an ASGI server: the application of CCDB_CONNECTION, made on first access"""
    if name == "app":
        global app
        app = create_app()
        return app
    raise AttributeError(name)
