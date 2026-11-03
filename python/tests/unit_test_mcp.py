"""The read-only MCP server (ccdb.mcp, docs/apis/mcp.md) through the SDK's in-memory client, on the test database.

Every tool answers; each answer equals the HTTP API's for the same arguments; the tool list names no write operation;
a provider whose write methods raise is never reached by any tool. Skipped without the mcp extra (Python 3.10+).
"""
import asyncio
import os
import tempfile
import unittest
from urllib.parse import quote

from ccdb import AlchemyProvider, testing
from ccdb.sql.sqlite_schema import create_sqlite_database

try:
    from mcp import Client
    from ccdb.mcp import create_server
    from fastapi.testclient import TestClient
    from ccdb.api import create_app
except ImportError:  # the mcp or the api extra is not installed
    Client = None

TABLE = "/test/test_vars/test_table"
WRITE_WORDS = ("add", "create", "delete", "remove", "update", "set_", "write", "edit", "deprecate", "upgrade", "insert", "drop")

# Every provider method that changes the database
WRITE_METHODS = [name for name in dir(AlchemyProvider) if name.split("_")[0] in ("create", "update", "delete", "set", "deprecate",
                                                                                   "undeprecate", "copy", "remove", "move")]


def setUpModule():
    global _restore_time_zone
    _restore_time_zone = testing.pin_time_zone("UTC")


def tearDownModule():
    _restore_time_zone()


@unittest.skipIf(Client is None, "the mcp extra is not installed")
class McpTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.directory = tempfile.TemporaryDirectory()
        path = os.path.join(cls.directory.name, "mcp.sqlite")
        create_sqlite_database(path)
        cls.connection = "sqlite:///" + path
        cls.server = create_server(cls.connection)
        cls.api = TestClient(create_app(cls.connection))

    @classmethod
    def tearDownClass(cls):
        cls.directory.cleanup()

    def call(self, name, **arguments):
        async def run():
            async with Client(self.server) as client:
                result = await client.call_tool(name, arguments)
                self.assertFalse(result.is_error, result)
                return result.structured_content
        content = asyncio.run(run())
        # a list answer arrives wrapped as {"result": [...]}
        return content["result"] if isinstance(content, dict) and set(content) == {"result"} else content

    def list_tools(self):
        async def run():
            async with Client(self.server) as client:
                return (await client.list_tools()).tools
        return asyncio.run(run())

    def api_json(self, url):
        response = self.api.get("/api/v1" + url, follow_redirects=True)
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def test_every_tool_answers_as_the_api(self):
        pairs = [
            (("instance_info", {}), "/instance"),
            (("list_directories", {}), "/directories"),
            (("list_tables", {"pattern": "test_tab*"}), "/tables?search=test_tab*"),
            (("table_info", {"path": TABLE}), "/tables" + TABLE),
            (("table_schema", {"path": TABLE}), None),
            (("list_variations", {}), "/variations"),
            (("list_tags", {}), "/tags"),
            (("resolve_request", {"request": TABLE + ":0:default"}), "/assignments?request=" + quote(TABLE + ":0:default")),
            (("list_versions", {"path": TABLE, "per_page": 25}), "/tables" + TABLE + "/versions?per_page=25"),
            (("search_log", {"per_page": 25}), "/logs?per_page=25"),
            (("compare_assignments", {"a": "1", "b": "4", "changed_only": False}), "/compare?a=1&b=4&changed=0"),
        ]
        for (name, arguments), url in pairs:
            with self.subTest(tool=name):
                answer = self.call(name, **arguments)
                if url:
                    self.assertEqual(answer, self.api_json(url))
                else:
                    self.assertEqual(answer["type"], "array")
        self.assertEqual(self.call("health")["status"], "ok")

    def test_readiness_answers_as_the_api(self):
        answer = self.call("readiness", stale_years=3)
        served = self.api_json("/readiness?stale_years=3")
        answer["config"].pop("generated"), served["config"].pop("generated")
        self.assertEqual(answer, served)

    def test_get_constants_pages_rows_with_the_stored_hash(self):
        answer = self.call("get_constants", request=TABLE + ":0:default", offset=1, limit=1)
        self.assertEqual(answer["rows"], [["2.5", "2.6", "2.7"]])
        self.assertEqual(answer["total_rows"], 2)
        self.assertEqual(answer["columns"], ["x", "y", "z"])
        self.assertEqual(answer["assignment"]["sha256"], self.api_json("/assignments/4")["sha256"])
        self.assertEqual(self.call("get_constants", assignment_id=4)["rows"], [["2.2", "2.3", "2.4"], ["2.5", "2.6", "2.7"]])

    def test_the_tool_list_names_no_write_operation(self):
        names = [tool.name for tool in self.list_tools()]
        self.assertEqual(len(names), 14)
        for name in names:
            self.assertFalse(any(word in name for word in WRITE_WORDS), name)

    def test_no_tool_reaches_a_write_method(self):
        self.assertIn("create_assignment", WRITE_METHODS)

        def refuse(name):
            def method(*args, **kwargs):
                raise AssertionError("the MCP server called the write method " + name)
            return method

        class ReadOnlyProvider(AlchemyProvider):
            pass
        for name in WRITE_METHODS:
            setattr(ReadOnlyProvider, name, refuse(name))

        def provider_factory():
            provider = ReadOnlyProvider()
            provider.connect(self.connection)
            return provider

        guarded = create_server(provider_factory=provider_factory)
        calls = {"instance_info": {}, "health": {}, "readiness": {"stale_years": 2}, "list_directories": {"include_deprecated": True},
                 "list_tables": {}, "table_info": {"path": TABLE}, "table_schema": {"path": TABLE}, "list_variations": {},
                 "list_tags": {}, "resolve_request": {"request": TABLE + ":0"}, "get_constants": {"request": TABLE + ":0"},
                 "list_versions": {"path": TABLE}, "compare_assignments": {"a": "1", "b": "4"}, "search_log": {}}

        async def run():
            async with Client(guarded) as client:
                tools = [tool.name for tool in (await client.list_tools()).tools]
                self.assertEqual(sorted(tools), sorted(calls))
                for name, arguments in calls.items():
                    result = await client.call_tool(name, arguments)
                    self.assertFalse(result.is_error, "{0}: {1}".format(name, result))
        asyncio.run(run())

    def test_errors_reach_the_agent_as_tool_errors(self):
        async def run():
            async with Client(self.server) as client:
                return await client.call_tool("table_info", {"path": "/no/such/table"})
        result = asyncio.run(run())
        self.assertTrue(result.is_error)


if __name__ == '__main__':
    unittest.main()
