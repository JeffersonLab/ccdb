"""The CCDB MCP server: read-only tools over a CCDB database for agents (docs/apis/mcp.md).

    ccdb -c mysql://ccdb_user@hallddb.jlab.org/ccdb mcp                # stdio, for a desktop agent
    ccdb -c mysql://ccdb_user@hallddb.jlab.org/ccdb mcp --http 8001    # streamable HTTP, for a shared instance

Every tool reads. No tool, resource or prompt writes to the database under any argument: the tools call the read-only
service functions of the HTTP API (ccdb.api.service), so an agent sees the values the API serves; the tests check
that the tool list names no write operation and that no tool reaches a write method of the provider. Resources are
the concepts pages of the documentation, when the CCDB checkout holds them.

Needs the mcp extra (Python 3.10 or newer): pip install 'ccdb[mcp]'.
"""
import contextlib
import functools
import os
from typing import Any, Dict, List

from ccdb import get_ccdb_home_path, version as ccdb_version_module

INSTRUCTIONS = """CCDB holds calibration constants of a physics experiment. Constants live in tables under directories
(/calorimeter/gains); a table has columns with types and units, and assignments: versions of its data for a run range
and a variation, each with its creation time. A request string names constants: /path:run:variation:time, any
trailing part optional (variation default, time newest), or /path:run@tag for the state a tag froze. A run selects the
assignment whose run range holds it; a variation falls back to its parent when it has no data; the newest assignment
created at or before the time wins. Times are UTC in answers; times you give are the server's local wall time,
any leading part of YYYY-MM-DD hh:mm:ss.ffffff, the latest moment it covers. Start with instance_info (readiness tells
how much of the metadata the instance documents) and list_directories or list_tables, then table_info, then resolve_request or get_constants."""

def create_server(connection_string=None, provider_factory=None):
    """The MCP server for one database. provider_factory (tests) replaces the per-call provider."""
    from mcp.server.mcpserver import MCPServer
    from mcp.server.mcpserver.exceptions import ToolError
    from mcp.types import ToolAnnotations
    from sqlalchemy.exc import NoResultFound
    from werkzeug.exceptions import HTTPException

    from ccdb.api import service
    from ccdb.errors import ObjectIsNotFoundInDbError
    from ccdb.api.database import Database, connection_from_environment

    database = None if provider_factory else Database(connection_string or connection_from_environment())

    @contextlib.contextmanager
    def provider():
        db = provider_factory() if provider_factory else database.provider()
        try:
            yield db
        finally:
            db.session.close()

    def dumped(value):
        if isinstance(value, list):
            return [each.model_dump(mode="json") if hasattr(each, "model_dump") else each for each in value]
        return value.model_dump(mode="json") if hasattr(value, "model_dump") else value

    server = MCPServer(name="ccdb", title="CCDB calibration constants (read-only)", instructions=INSTRUCTIONS,
                       version=ccdb_version_module.version)

    def tool(description):
        """Registers a read-only tool with structured output; a missing object or a bad argument reaches the agent as
        a tool error with its message, not as an internal error"""
        def register(function):
            @functools.wraps(function)
            def guarded(*args, **kwargs):
                try:
                    return function(*args, **kwargs)
                except (ObjectIsNotFoundInDbError, NoResultFound, LookupError, ValueError) as error:
                    raise ToolError(str(error) or type(error).__name__)
                except HTTPException as error:
                    raise ToolError(error.description)
            server.tool(description=description, structured_output=True,
                        annotations=ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True))(guarded)
            return function
        return register

    @tool("The CCDB version, the schema version and the instance properties (experiment, description, "
                             "license, citation, contact, url).")
    def instance_info() -> Dict[str, Any]:
        with provider() as db:
            return dumped(service.instance(db))

    @tool("The readiness profile of the instance, as `ccdb db readiness --json`: how many columns have units, tables a "
          "description, versions a comment; open-ended run ranges; versions by anonymous; stale and empty tables; shared "
          "constant sets; which instance properties (license, citation, contact) are set. A table is stale when no "
          "version of it was created in the last stale_years years.")
    def readiness(stale_years: int = 5) -> Dict[str, Any]:
        with provider() as db:
            return service.readiness(db, stale_years)

    @tool("Whether the database answers: status ok or error, and the CCDB version.")
    def health() -> Dict[str, Any]:
        try:
            with provider() as db:
                db.session.execute(__import__("sqlalchemy").text("SELECT 1"))
            return {"status": "ok", "version": ccdb_version_module.version}
        except Exception:
            return {"status": "error", "version": ccdb_version_module.version}

    @tool("Every directory, by path, with its comment. Deprecated directories are hidden unless "
                             "include_deprecated is true.")
    def list_directories(include_deprecated: bool = False) -> List[Dict[str, Any]]:
        with provider() as db:
            return dumped(service.directories(db, include_deprecated))

    @tool("Tables whose name matches a pattern with * and ? (all tables for *): path, rows, column "
                             "count, comment. Deprecated tables are hidden unless include_deprecated is true.")
    def list_tables(pattern: str = "*", include_deprecated: bool = False) -> List[Dict[str, Any]]:
        with provider() as db:
            return dumped(service.tables(db, pattern, include_deprecated))

    @tool("One table by path: its columns with types, units and comments, its properties, the "
                             "variations that have data, the assignment count and the newest assignment.")
    def table_info(path: str) -> Dict[str, Any]:
        with provider() as db:
            return dumped(service.table(db, path))

    @tool("A JSON Schema (2020-12) of the rows of a table's data: one string per cell, with the "
                             "column type, units and comment.")
    def table_schema(path: str) -> Dict[str, Any]:
        with provider() as db:
            return service.table_schema(db, path)

    @tool("Every variation with its comment, parent and ancestry. Deprecated variations are hidden "
                             "unless include_deprecated is true.")
    def list_variations(include_deprecated: bool = False) -> List[Dict[str, Any]]:
        with provider() as db:
            return dumped(service.variations(db, include_deprecated))

    @tool("Every tag: a named snapshot of one variation at one UTC moment, as used in a request "
                             "/path:run@tag, with its properties (description, software, container, data, rucio_did, doi).")
    def list_tags() -> List[Dict[str, Any]]:
        with provider() as db:
            return dumped(service.tags(db))

    @tool("The assignment a request string resolves to (/path:run:variation:time or /path:run@tag): "
                             "id, request, variation, run range, UTC creation time, author, comment, the SHA-256 and "
                             "size of its data, its columns. Give tag to read the request under a tag.")
    def resolve_request(request: str, tag: str = "") -> Dict[str, Any]:
        with provider() as db:
            found, _ = service.resolve(db, request_string=_with_tag(request, tag))
            return dumped(service.assignment(db, found))

    @tool("The constants of an assignment, by request string (or by assignment_id), a page of rows: "
                             "offset and limit count rows. Every cell is the text stored. Also returns the columns, the "
                             "total row count and the SHA-256 of the stored data. Give tag to read under a tag.")
    def get_constants(request: str = "", assignment_id: int = 0, tag: str = "", offset: int = 0, limit: int = 100) -> Dict[str, Any]:
        if offset < 0 or not 1 <= limit <= 10000:
            raise ValueError("offset must be 0 or more and limit 1 to 10000")
        with provider() as db:
            if assignment_id:
                found, _ = service.resolve(db, assignment_id=assignment_id)
            else:
                found, _ = service.resolve(db, request_string=_with_tag(request, tag))
            rows = found.constant_set.data_table
            info = service.assignment(db, found)
            return {"assignment": dumped(info), "columns": [column["name"] for column in dumped(info)["columns"]],
                    "total_rows": len(rows), "offset": offset, "rows": rows[offset:offset + limit]}

    @tool("A page of a table's assignments (versions), newest first by default, as `ccdb vers`: "
                             "page, per_page (25, 50, 100, 200), sort (created, run_min, run_max, variation, author, id), "
                             "order (asc, desc), and filters variation and run.")
    def list_versions(path: str, page: int = 1, per_page: int = 50, sort: str = "created", order: str = "desc",
                      variation: str = "", run: int = -1) -> Dict[str, Any]:
        args = {"page": str(page), "per_page": str(per_page), "sort": sort, "order": order}
        with provider() as db:
            return dumped(service.versions(db, path, args, variation or None, run if run >= 0 else None))

    @tool("Two assignments of one table compared cell by cell (each a request string or an id): "
                             "the changed cells with the a and b value, the counts of changed cells and rows, and both "
                             "sides' metadata. changed_only keeps only the rows with a change.")
    def compare_assignments(a: str, b: str, changed_only: bool = True) -> Dict[str, Any]:
        with provider() as db:
            side_a, side_b, _ = service.compare_pair(db, a, b)
            return service.compare(side_a, side_b, changed_only)

    @tool("A page of the change log, newest first: who added, changed or removed what and when. "
                             "search matches the description and the author name (for example a table path).")
    def search_log(search: str = "", page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        args = {"page": str(page), "per_page": str(per_page), "search": search}
        with provider() as db:
            return dumped(service.logs(db, args))

    for page_path in concept_pages():
        name = os.path.splitext(os.path.basename(page_path))[0]
        server.add_resource(_page_resource(page_path, name))
    return server


def _with_tag(request, tag):
    if not tag:
        return request
    if "@" in request:
        raise ValueError("Give the tag either in the request (@NAME) or as tag, not both")
    return "{0}@{1}".format(request, tag)


def concept_pages():
    """The concepts pages of the documentation in the CCDB checkout, if it holds them"""
    directory = os.path.join(get_ccdb_home_path(), "docs", "concepts")
    if not os.path.isdir(directory):
        return []
    return sorted(os.path.join(directory, name) for name in os.listdir(directory) if name.endswith(".md"))


def _page_resource(path, name):
    from pathlib import Path
    from mcp.server.mcpserver.resources import FileResource
    return FileResource(uri="ccdb://docs/concepts/{0}".format(name), name=name, path=Path(path), mime_type="text/markdown",
                        description="CCDB documentation: {0}".format(name.replace("-", " ")))
