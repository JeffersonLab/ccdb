"""Error responses of the web GUI.

Pages answer 400 and 404 with the one error template. A view raises `abort(400, description)` or
`abort(404, description)`, or lets `ObjectIsNotFoundInDbError` from the provider propagate; the
handlers below turn both into the page with the right status. Unknown URLs go through the same 404
handler. Anything else stays an unhandled exception, so Flask logs it and answers 500.

Fragments that the tree loads into a modal answer plain text instead (see views.py); a view that
returns `(text, 404)` itself never enters these handlers.
"""
from flask import render_template
from werkzeug.exceptions import BadRequest, NotFound

from ccdb.errors import ObjectIsNotFoundInDbError


def register(app):

    @app.errorhandler(BadRequest)
    @app.errorhandler(NotFound)
    def http_error(error):
        return render_template("error.html", status=error.code, title=error.name, message=error.description), error.code

    @app.errorhandler(ObjectIsNotFoundInDbError)
    def not_in_database(error):
        return render_template("error.html", status=404, title="Not Found", message=str(error)), 404
