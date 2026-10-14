"""The URL list shared by the smoke suite, the golden comparison and the browser check.

Paths refer to objects that make_fixture.py creates; keep the two files in step.
Each entry: (label, url, kind). kind is "page" for a full HTML page a person opens,
"fragment" for HTML loaded into a modal, "data" for text or JSON (a redirect to it counts),
"edge" for a request that must answer with an error or a redirect and never with a server error.
The --check modes of smoke.py and browse.py enforce the status each kind allows.
"""
from urllib.parse import quote

BIG_TABLE = "/calib/fcal/gains"                 # 3600 assignments over 6 variations
SMALL_TABLE = "/test/test_vars/test_table"      # standard test content, a handful of assignments
DEEP_TABLE = "/deep/l1/l2/l3/l4/l5/l6/bottom"   # bottom of the 7-level directory chain
HOSTILE_TABLE = "/hostile/x\"y'z&<script>alert(1)<b>"
UNICODE_TABLE = "/hostile/unicode_Привет_✓"

PAGES = [
    ("tree", "/", "page"),
    ("tree_alias", "/tree", "page"),
    ("dirs_debug", "/dirs", "edge"),             # retired route: answers 404
    ("hello", "/hello", "edge"),                 # retired route: answers 404
    ("variations", "/vars", "page"),
    ("logs", "/logs", "page"),
    ("doc", "/doc", "page"),
    ("request_form", "/test_request", "page"),
    ("versions_big", "/versions" + BIG_TABLE, "page"),
    ("versions_small", "/versions" + SMALL_TABLE, "page"),
    ("versions_deep", "/versions" + DEEP_TABLE, "page"),
    ("versions_hostile", "/versions" + quote(HOSTILE_TABLE), "page"),
    ("versions_unicode", "/versions" + quote(UNICODE_TABLE), "page"),
    ("versions_missing", "/versions/no/such/table", "edge"),
    ("dir_info", "/get-dir-info/1", "fragment"),
    ("dir_info_missing", "/get-dir-info/999999", "edge"),
    ("table_info", "/get-table-info/1", "fragment"),
    ("table_info_missing", "/get-table-info/999999", "edge"),
    ("show_small", "/show_request?request=" + quote(SMALL_TABLE + ":0:default"), "page"),
    ("show_big", "/show_request?request=" + quote(BIG_TABLE + ":1500:default"), "page"),
    ("show_big_mc", "/show_request?request=" + quote(BIG_TABLE + ":1500:mc"), "page"),
    ("show_hostile", "/show_request?request=" + quote(HOSTILE_TABLE + ":0:default"), "page"),
    ("show_bad_variation", "/show_request?request=" + quote(BIG_TABLE + ":1:nosuchvar"), "edge"),
    ("show_missing_table", "/show_request?request=" + quote("/no/such/table:1"), "edge"),
    ("show_empty", "/show_request", "edge"),
    ("dump_small", "/dowload_request?request=" + quote(SMALL_TABLE + ":0:default"), "data"),
    ("dump_hostile", "/dowload_request?request=" + quote(HOSTILE_TABLE + ":0:default"), "data"),
    ("dump_empty", "/dowload_request", "edge"),
    ("dump_spelled_right", "/download_request?request=" + quote(SMALL_TABLE + ":0:default"), "edge"),
    # paginated routes and request parsing
    ("versions_page2", "/versions" + BIG_TABLE + "?page=2&per_page=200", "page"),
    ("versions_page0", "/versions" + BIG_TABLE + "?page=0", "edge"),
    ("versions_per_page7", "/versions" + BIG_TABLE + "?per_page=7", "edge"),
    ("versions_sort_bad", "/versions" + BIG_TABLE + "?sort=nope", "edge"),
    ("versions_page9999", "/versions" + BIG_TABLE + "?page=9999", "edge"),
    ("versions_filtered", "/versions" + BIG_TABLE + "?variation=mc&run=1500&search=bob", "page"),
    ("logs_page2", "/logs?page=2&per_page=100&search=alice", "page"),
    ("show_garbage", "/show_request?request=garbage", "edge"),
    ("show_bad_run", "/show_request?request=" + quote(BIG_TABLE + ":abc"), "edge"),
    ("no_such_url", "/no/such/url", "edge"),
    # the assignment resolver: the request string and the id address the same assignment
    ("assignment_by_id", "/assignments/4", "page"),
    ("assignment_missing_id", "/assignments/999999", "edge"),
    ("json_by_request", "/assignments/data.json?request=" + quote(BIG_TABLE + ":1500:default"), "data"),
    ("json_by_id", "/assignments/4/data.json", "data"),
    ("json_empty", "/assignments/data.json", "edge"),
    ("txt_by_request", "/assignments/data.txt?request=" + quote(HOSTILE_TABLE + ":0:default"), "data"),
    ("txt_by_id", "/assignments/4/data.txt", "data"),
    # the health route and the tree with a prefilled filter
    ("health", "/health", "data"),
    ("tree_filtered", "/?filter=/calib", "page"),
]

# What a person opens in a browser: every page once (the tree alias duplicates the tree) plus one
# deliberate 404, so the error page is checked in both themes and both viewports too.
BROWSER_PAGES = [p for p in PAGES if p[2] == "page" and p[0] != "tree_alias"] + [
    ("versions_missing", "/versions/no/such/table", "edge"),
]
