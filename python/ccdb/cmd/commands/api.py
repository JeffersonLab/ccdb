"""
Runs the CCDB HTTP API (ccdb.api) on the connection of the command line
"""
import logging

from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb.provider import hide_password

log = logging.getLogger("ccdb.cmd.commands.api")


class HttpApi(CliCommandBase):
    """Starts the HTTP API with uvicorn"""

    command = "api"
    name = "HttpApi"
    short_descr = "Starts the read-only HTTP API (needs the api extra: pip install ccdb[api])"
    uses_db = False  # the API opens its own engine

    def execute(self, args):
        parsed_args = self.process_arguments(args)
        try:
            import uvicorn
            from ccdb.api import create_app
        except ImportError as error:
            log.critical("The HTTP API needs the api extra: pip install 'ccdb[api]' ({0})".format(error))
            return False

        connection_string = self.context.connection_string
        app = create_app(connection_string)
        # Connect and check the schema before the server starts, so a wrong connection string fails here
        try:
            app.state.database.ensure_engine()
        except Exception as ex:
            log.critical("CCDB HTTP API unable to connect to {0}. Exception details: {1}".format(
                hide_password(connection_string), hide_password(str(ex), connection_string)))
            return False
        uvicorn.run(app, host=parsed_args.host, port=int(parsed_args.port))
        return True

    @staticmethod
    def process_arguments(args):
        parser = UtilityArgumentParser()
        parser.add_argument("-p", "--port", default=8000)
        parser.add_argument("--host", default="127.0.0.1")
        return parser.parse_args(args)

    def print_help(self):
        print("""Starts the read-only CCDB HTTP API on this connection (docs/apis/http.md).

    ccdb -c <connection> api [-p PORT] [--host HOST]

    -p, --port   port to listen on, 8000 by default
    --host       address to listen on, 127.0.0.1 by default; 0.0.0.0 listens on every interface

The OpenAPI document is http://HOST:PORT/api/v1/openapi.json, the interactive page /api/v1/docs.
A deployment runs `uvicorn ccdb.api:app` with CCDB_CONNECTION set, behind a cache (docker/nginx/ccdb-api.conf).
""")
