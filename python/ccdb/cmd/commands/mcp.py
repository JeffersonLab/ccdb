"""
Runs the read-only CCDB MCP server (ccdb.mcp) on the connection of the command line
"""
import logging

from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb.provider import hide_password

log = logging.getLogger("ccdb.cmd.commands.mcp")


class McpServer(CliCommandBase):
    """Starts the MCP server over stdio or streamable HTTP"""

    command = "mcp"
    name = "McpServer"
    short_descr = "Starts the read-only MCP server for agents (needs the mcp extra: pip install ccdb[mcp])"
    uses_db = False  # the server opens its own engine

    def execute(self, args):
        parsed_args = self.process_arguments(args)
        try:
            from ccdb.mcp import create_server
        except ImportError as error:
            log.critical("The MCP server needs the mcp extra (Python 3.10+): pip install 'ccdb[mcp]' ({0})".format(error))
            return False
        connection_string = self.context.connection_string
        try:
            server = create_server(connection_string)
        except Exception as ex:
            log.critical("CCDB MCP server unable to start on {0}: {1}".format(hide_password(connection_string),
                                                                             hide_password(str(ex), connection_string)))
            return False
        if parsed_args.http:
            server.run("streamable-http", host=parsed_args.host, port=int(parsed_args.http))
        else:
            server.run("stdio")
        return True

    @staticmethod
    def process_arguments(args):
        parser = UtilityArgumentParser()
        parser.add_argument("--http", metavar="PORT", default="", help="serve streamable HTTP on this port instead of stdio")
        parser.add_argument("--host", default="127.0.0.1")
        return parser.parse_args(args)

    def print_help(self):
        print("""Starts the read-only CCDB MCP server for agents on this connection (docs/apis/mcp.md).

    ccdb -c <connection> mcp                       # stdio: an agent starts this command itself
    ccdb -c <connection> mcp --http 8001 [--host 0.0.0.0]   # streamable HTTP at http://HOST:8001/mcp

No tool writes to the database.
""")
