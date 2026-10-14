"""WSGI entry point of the CCDB web GUI: `gunicorn ccdbweb:app`.

The connection string comes from CCDB_CONNECTION, the same variable the ccdb command reads.
Not set → the import fails with the message below, so a misconfigured server stops at startup
instead of answering 500 to every request.
"""
import ccdb.webgui
from ccdb.webgui.db import NO_CONNECTION_MESSAGE

connection_string = ccdb.webgui.connection_string_from_env()
if not connection_string:
    raise SystemExit(NO_CONNECTION_MESSAGE)

app = ccdb.webgui.cerate_ccdb_flask_app(connection_string)

if __name__ == "__main__":
    # Run the app in debug mode when executed directly
    app.run(debug=True)
