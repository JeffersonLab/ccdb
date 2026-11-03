"""Error answers of the HTTP API: JSON `{"status": <code>, "error": "<message>"}`, never cached.

The web GUI's helpers that the API shares raise werkzeug's HTTP errors (400 for a malformed request string, 404 for
an unknown object); they map to the same codes here. A missing object is 404, a malformed parameter 400.
"""
import logging

from fastapi.exceptions import RequestValidationError
from fastapi.responses import Response
from sqlalchemy.exc import NoResultFound
from werkzeug.exceptions import HTTPException

from ccdb.errors import DatabaseStructureError, ObjectIsNotFoundInDbError

from .responses import JSON, dump_json

log = logging.getLogger("ccdb.api")


def error_response(status, message):
    return Response(content=dump_json({"status": status, "error": message}), status_code=status, media_type=JSON,
                    headers={"Cache-Control": "no-store"})


def install_error_handlers(app):
    @app.exception_handler(HTTPException)
    def werkzeug_error(request, error):
        return error_response(error.code or 500, error.description)

    @app.exception_handler(ObjectIsNotFoundInDbError)
    @app.exception_handler(NoResultFound)
    @app.exception_handler(LookupError)
    def not_found(request, error):
        return error_response(404, str(error) or "Not found")

    @app.exception_handler(ValueError)
    def bad_request(request, error):
        return error_response(400, str(error))

    @app.exception_handler(RequestValidationError)
    def bad_parameter(request, error):
        details = "; ".join("{0}: {1}".format(".".join(str(part) for part in each["loc"][1:]) or "request", each["msg"])
                            for each in error.errors())
        return error_response(400, details)

    @app.exception_handler(DatabaseStructureError)
    def wrong_database(request, error):
        log.warning("CCDB HTTP API database error: %s", error)
        return error_response(503, "The database is not a CCDB schema 6 database")
