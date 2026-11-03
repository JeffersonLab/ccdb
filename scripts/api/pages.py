"""The URL list of the HTTP API ruler: smoke.py requests every entry, golden.py checks their answers.

Paths refer to objects that scripts/webgui/make_fixture.py creates; keep the files in step.
Each entry: (label, url, kind). kind is "json" for a JSON answer (200), "data" for an assignment data form (200),
"redirect" for a resolving request (302), "file" for a bundle (200 after its redirect), "edge" for a request that
must answer an error and never a server error.
"""
from urllib.parse import quote

BIG_TABLE = "/calib/fcal/gains"
KV_TABLE = "/calib/ccal/parms"
SMALL_TABLE = "/test/test_vars/test_table"
UNICODE_TABLE = "/hostile/unicode_Привет_✓"
CHANNELS_TABLE = "/calib/ccal/channels"
SHARED_TABLE = "/schema6/shared"
NUMERIC_TABLE = "/schema6/numeric"
RETIRED_TABLE = "/schema6/retired_table"

# Assignments whose data forms the golden data checks against the web GUI and the stored hash
DATA_ASSIGNMENTS = [3612, 3613, 3614, 3615, 3616, 3617]

PAGES = [
    ("health", "/api/v1/health", "json"),
    ("instance", "/api/v1/instance", "json"),
    ("openapi", "/api/v1/openapi.json", "json"),
    ("directories", "/api/v1/directories", "json"),
    ("directories_all", "/api/v1/directories?deprecated=all", "json"),
    ("directory", "/api/v1/directories/calib/fcal", "json"),
    ("directory_missing", "/api/v1/directories/no/such", "edge"),
    ("tables", "/api/v1/tables", "json"),
    ("tables_search", "/api/v1/tables?search=gain*", "json"),
    ("tables_all", "/api/v1/tables?deprecated=all", "json"),
    ("tables_bad_deprecated", "/api/v1/tables?deprecated=yes", "edge"),
    ("table_big", "/api/v1/tables" + BIG_TABLE, "json"),
    ("table_kv", "/api/v1/tables" + KV_TABLE, "json"),
    ("table_unicode", "/api/v1/tables" + quote(UNICODE_TABLE), "json"),
    ("table_retired", "/api/v1/tables" + RETIRED_TABLE, "json"),
    ("table_missing", "/api/v1/tables/no/such", "edge"),
    ("schema_channels", "/api/v1/tables" + CHANNELS_TABLE + "/schema", "json"),
    ("card_big", "/api/v1/tables" + BIG_TABLE + "/card", "json"),
    ("card_shared", "/api/v1/tables" + SHARED_TABLE + "/card", "json"),
    ("card_unicode", "/api/v1/tables" + quote(UNICODE_TABLE) + "/card", "json"),
    ("card_retired", "/api/v1/tables" + RETIRED_TABLE + "/card", "json"),
    ("card_missing", "/api/v1/tables/no/such/card", "edge"),
    ("versions_big", "/api/v1/tables" + BIG_TABLE + "/versions", "json"),
    ("versions_big_page", "/api/v1/tables" + BIG_TABLE + "/versions?page=7&per_page=100&sort=run_min&order=asc", "json"),
    ("versions_big_filter", "/api/v1/tables" + BIG_TABLE + "/versions?variation=mc&run=1500", "json"),
    ("versions_bad_sort", "/api/v1/tables" + BIG_TABLE + "/versions?sort=nonsense", "edge"),
    ("variations", "/api/v1/variations", "json"),
    ("variations_all", "/api/v1/variations?deprecated=all", "json"),
    ("variation", "/api/v1/variations/mc", "json"),
    ("variation_missing", "/api/v1/variations/no_such", "edge"),
    ("run_ranges", "/api/v1/run-ranges", "json"),
    ("tags", "/api/v1/tags", "json"),
    ("tag", "/api/v1/tags/fixture_past", "json"),
    ("tag_missing", "/api/v1/tags/no_such_tag", "edge"),
    ("logs", "/api/v1/logs", "json"),
    ("logs_search", "/api/v1/logs?search=gains&per_page=25", "json"),
    ("log", "/api/v1/logs/1", "json"),
    ("log_missing", "/api/v1/logs/99999999", "edge"),
    ("logs_atom", "/api/v1/logs.atom", "data"),
    ("logs_atom_search", "/api/v1/logs.atom?search=gains&per_page=25", "data"),
    ("assignment", "/api/v1/assignments/3612", "json"),
    ("assignment_request", "/api/v1/assignments?request=" + quote(SMALL_TABLE + ":0:default"), "redirect"),
    ("assignment_exact", "/api/v1/assignments?request=" + quote(CHANNELS_TABLE + ":0:default:2020-01-06_10-02-00"), "json"),
    ("assignment_tag", "/api/v1/assignments?request=" + quote(SHARED_TABLE + ":0@fixture_newest"), "json"),
    ("assignment_missing", "/api/v1/assignments/99999999", "edge"),
    ("assignment_malformed", "/api/v1/assignments?request=" + quote(SMALL_TABLE + ":abc"), "edge"),
    ("data_raw", "/api/v1/assignments/3612/data", "data"),
    ("data_json", "/api/v1/assignments/3612/data.json", "data"),
    ("data_txt", "/api/v1/assignments/3612/data.txt", "data"),
    ("data_request", "/api/v1/assignments/data.json?request=" + quote(BIG_TABLE + ":1500:mc"), "redirect"),
    ("data_bad_form", "/api/v1/assignments/3612/data.xml", "edge"),
    ("compare", "/api/v1/compare?a=3612&b=3613", "json"),
    ("compare_changed", "/api/v1/compare?a=3612&b=3613&changed=1", "json"),
    ("compare_diff", "/api/v1/compare.diff?a=3612&b=3613", "data"),
    ("compare_tables_differ", "/api/v1/compare?a=3612&b=3616", "edge"),
    ("bundle_newest", "/api/v1/bundle?run=1500", "redirect"),
    ("bundle_tag", "/api/v1/bundle?run=1500&tag=fixture_past", "file"),
    ("bundle_both", "/api/v1/bundle?run=1500&tag=fixture_past&variation=mc", "edge"),
]

ALLOWED_STATUS = {"json": (200,), "data": (200,), "redirect": (302,), "file": (200,)}
