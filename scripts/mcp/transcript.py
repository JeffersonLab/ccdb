#!/usr/bin/env python3
"""A recorded agent session with the CCDB MCP server, for docs/apis/mcp.md: reproducible, no language model involved.

    python scripts/mcp/transcript.py > transcript.md
    python scripts/mcp/transcript.py --check docs/apis/mcp.md    # exit 1 unless the page holds this session

It builds the ePIC-shaped demo tables (scripts/demo/make_epic_tables.py) in a temporary SQLite file, connects the MCP
SDK's in-memory client to ccdb.mcp, and asks the question an agent gets: "What changed in /epic/HCal/adc_calib between
run periods 1-999 and 1000-1999, and who changed it?". Each step prints the tool call and the part of the answer the
next step uses, in Markdown.
"""
import asyncio
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TABLE = "/epic/HCal/adc_calib"


def load_generator():
    path = os.path.join(HERE, "..", "demo", "make_epic_tables.py")
    spec = importlib.util.spec_from_file_location("make_epic_tables", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def show(title, call, answer):
    print("**{0}**\n\n```\n{1}\n```\n\n```json\n{2}\n```\n".format(title, call, json.dumps(answer, indent=1, ensure_ascii=False)))


async def session(connection):
    from mcp import Client
    from ccdb.mcp import create_server

    async def call(client, name, **arguments):
        result = await client.call_tool(name, arguments)
        content = result.structured_content
        return content["result"] if isinstance(content, dict) and set(content) == {"result"} else content

    async with Client(create_server(connection)) as client:
        profile = await call(client, "readiness")
        show("1. Check what the instance documents", "readiness()",
             {"metadata": profile["metadata"], "instance": profile["instance"]})

        tables = await call(client, "list_tables", pattern="adc_calib")
        show("2. Find the table", 'list_tables(pattern="adc_calib")', [each["path"] for each in tables])

        info = await call(client, "table_info", path=TABLE)
        show("3. Read what it holds", 'table_info(path="{0}")'.format(TABLE),
             {key: info[key] for key in ("comment", "variations", "assignments")} |
             {"columns": ["{0} [{1}]".format(c["name"], c["units"]) if c["units"] else c["name"] for c in info["columns"]]})

        versions = await call(client, "list_versions", path=TABLE, variation="default", sort="run_min", order="asc")
        show("4. List the versions of the default variation", 'list_versions(path="{0}", variation="default", sort="run_min", order="asc")'.format(TABLE),
             [{key: row[key] for key in ("id", "run_min", "run_max", "created", "author", "comment")} for row in versions["items"]])

        compared = await call(client, "compare_assignments", a="{0}:500:default".format(TABLE), b="{0}:1500:default".format(TABLE))
        changed = [{"row": row["row"], "cells": [cell for cell in row["cells"] if cell["changed"]]} for row in compared["rows"]]
        show("5. Compare a run of each period", 'compare_assignments(a="{0}:500:default", b="{0}:1500:default")'.format(TABLE),
             {"changed_cells": compared["changed_cells"], "changed_rows": compared["changed_rows"], "rows": changed})

        log = await call(client, "search_log", search=TABLE, per_page=25)
        show("6. Who changed it", 'search_log(search="{0}")'.format(TABLE),
             [{key: row[key] for key in ("created", "author", "action", "description")} for row in log["items"]][:3])


def main():
    sys.path.insert(0, os.path.join(HERE, "..", "..", "python"))
    generator = load_generator()
    output = io.StringIO()
    with tempfile.TemporaryDirectory() as directory:
        connection = "sqlite:///" + os.path.join(directory, "epic_demo.sqlite")
        generator.build(connection)
        with contextlib.redirect_stdout(output):
            asyncio.run(session(connection))
    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        with open(sys.argv[2], encoding="utf-8") as page:
            if output.getvalue() not in page.read():
                sys.exit("{0} does not hold the session this script records; regenerate it".format(sys.argv[2]))
        print("{0} holds the recorded session".format(sys.argv[2]))
    else:
        sys.stdout.write(output.getvalue())


if __name__ == "__main__":
    main()
