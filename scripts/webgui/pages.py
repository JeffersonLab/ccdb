"""The URL list shared by the smoke suite, the golden comparison and the browser check.

Paths refer to objects that make_fixture.py creates; keep the two files in step.
Each entry: (label, url, kind). kind is "page" for a full HTML page a person opens,
"fragment" for HTML loaded into a modal, "data" for text or JSON (a redirect to it counts),
"edge" for a request that must answer with an error or a redirect and never with a server error.
The --check modes of smoke.py and browse.py enforce the status each kind allows.
"""
from urllib.parse import quote

BIG_TABLE = "/calib/fcal/gains"                 # 3600 assignments over 6 variations
KV_TABLE = "/calib/ccal/parms"                  # one row, six columns: shown vertically by default
SMALL_TABLE = "/test/test_vars/test_table"      # standard test content, a handful of assignments
DEEP_TABLE = "/deep/l1/l2/l3/l4/l5/l6/bottom"   # bottom of the 7-level directory chain
HOSTILE_TABLE = "/hostile/x\"y'z&<script>alert(1)<b>"
UNICODE_TABLE = "/hostile/unicode_Привет_✓"
CHANNELS_TABLE = "/calib/ccal/channels"            # 600 rows × 4 columns, two default assignments (ids 3612, 3613) that differ in seven cells
CHANNELS_FIRST = quote(CHANNELS_TABLE + ":0:default:2020-01-06_10-02-00")   # the first of the two by its exact request string

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
    # data layouts: auto (vertical for one row and more than two columns), forced, and a bad value
    ("show_kv", "/show_request?request=" + quote(KV_TABLE + ":0:default"), "page"),
    ("show_kv_horizontal", "/show_request?request=" + quote(KV_TABLE + ":0:default") + "&layout=horizontal", "page"),
    ("show_big_vertical", "/show_request?request=" + quote(BIG_TABLE + ":1500:default") + "&layout=vertical", "page"),
    ("show_big_horizontal", "/show_request?request=" + quote(BIG_TABLE + ":1500:default") + "&layout=horizontal", "page"),
    ("assignment_by_id_vertical", "/assignments/4?layout=vertical", "page"),
    ("show_bad_layout", "/show_request?request=" + quote(KV_TABLE + ":0:default") + "&layout=sideways", "edge"),
    # compare variations: the form, a chain segment of one and of two variations, the filters, the empty case,
    # the root, and the bad inputs
    ("compare_form", "/vars/compare", "page"),
    ("compare_calib_v2", "/vars/compare?variation=calib_v2", "page"),
    ("compare_calib_v2_default", "/vars/compare?variation=calib_v2&parent=default", "page"),
    ("compare_run", "/vars/compare?variation=calib_v2&run=1500", "page"),
    ("compare_time", "/vars/compare?variation=calib_v2&parent=default&time=2020-01-02", "page"),
    ("compare_subsubtest", "/vars/compare?variation=subsubtest", "page"),
    ("compare_root", "/vars/compare?variation=default", "page"),
    ("compare_unknown", "/vars/compare?variation=nosuch", "edge"),
    ("compare_bad_parent", "/vars/compare?variation=calib_v2&parent=mc", "edge"),
    ("compare_bad_run", "/vars/compare?variation=calib_v2&run=abc", "edge"),
    ("compare_bad_time", "/vars/compare?variation=calib_v2&time=yesterday", "edge"),
    # compare assignments: the form (alone, with a table, with one side), pairs by request string, by id and mixed,
    # the parts form (redirects to the canonical URL), the same assignment twice, and the bad inputs
    ("diff_form", "/compare", "page"),
    ("diff_form_table", "/compare?table=" + CHANNELS_TABLE, "page"),
    ("diff_form_one_side", "/compare?table=" + CHANNELS_TABLE + "&a=" + CHANNELS_FIRST, "page"),
    ("diff_channels", "/compare?a=" + CHANNELS_FIRST + "&b=" + quote(CHANNELS_TABLE + ":0:default"), "page"),
    ("diff_by_id", "/compare?a=3612&b=3613", "page"),
    ("diff_parms_mixed", "/compare?a=3610&b=" + quote(KV_TABLE + ":0:calib"), "page"),
    ("diff_same", "/compare?a=3612&b=3612", "page"),
    # the per-cell view: changed rows only, the vertical layout, the third page, and the one-row pair (auto → vertical)
    ("diff_changed_only", "/compare?a=3612&b=3613&changed=1", "page"),
    ("diff_vertical", "/compare?a=3612&b=3613&layout=vertical&changed=1", "page"),
    ("diff_horizontal", "/compare?a=3612&b=3613&layout=horizontal&changed=1", "page"),
    ("diff_page3", "/compare?a=3612&b=3613&page=3", "page"),
    ("diff_parms", "/compare?a=3610&b=3611", "page"),
    # the per-column view, horizontal (changed rows) and vertical (the one-row pair)
    ("diff_columns", "/compare?a=3612&b=3613&view=columns&changed=1", "page"),
    ("diff_columns_vertical", "/compare?a=3610&b=3611&view=columns", "page"),
    # the table-to-table view, horizontal (changed rows) and vertical (the one-row pair)
    ("diff_tables", "/compare?a=3612&b=3613&view=tables&changed=1", "page"),
    ("diff_tables_vertical", "/compare?a=3610&b=3611&view=tables", "page"),
    # the assignment pages of the channels pair: the second has a previous assignment (Compare with previous), the first has none
    ("assignment_channels_second", "/assignments/3613", "page"),
    ("assignment_channels_first", "/assignments/3612", "page"),
    # the paged data table of a 600-row assignment: the last page, a smaller page size, a page past the end (clamped), a bad page
    ("assignment_channels_page3", "/assignments/3613?page=3", "page"),
    ("assignment_channels_per_page50", "/assignments/3613?per_page=50&page=12", "page"),
    ("assignment_channels_page9999", "/assignments/3613?page=9999", "page"),
    ("assignment_channels_page0", "/assignments/3613?page=0", "edge"),
    # log record pages: the newest record (a 60-line comment), a hostile comment, a missing id
    ("log_record", "/logs/2414", "page"),
    ("log_record_hostile", "/logs/14", "page"),
    ("log_record_directory", "/logs/13", "page"),      # names directory 5
    ("log_record_table", "/logs/2415", "page"),         # names the channels table
    ("log_record_variation", "/logs/2416", "page"),     # names calib_v2
    ("log_record_deleted", "/logs/2417", "page"),       # names a table that does not exist: text, no link
    ("log_record_missing", "/logs/999999", "edge"),
    # the comparison as JSON, and its bad inputs
    ("diff_json", "/compare/data.json?a=3612&b=3613&changed=1", "data"),
    ("diff_json_by_request", "/compare/data.json?a=" + CHANNELS_FIRST + "&b=" + quote(CHANNELS_TABLE + ":0:default") + "&changed=1", "data"),
    ("diff_json_empty", "/compare/data.json", "edge"),
    ("diff_json_two_tables", "/compare/data.json?a=3610&b=3613", "edge"),
    ("diff_form_parts", "/compare?table=" + KV_TABLE + "&a_variation=default&b_variation=calib", "edge"),
    ("diff_unknown_side", "/compare?a=" + quote("/no/such/table:0") + "&b=3613", "edge"),
    ("diff_malformed_side", "/compare?a=garbage&b=3613", "edge"),
    ("diff_huge_id", "/compare?a=99999999999999999999&b=3613", "edge"),
    ("diff_two_tables", "/compare?a=3610&b=3613", "edge"),
    ("diff_unknown_table", "/compare?table=/no/such/table", "edge"),
    ("diff_bad_view", "/compare?a=3612&b=3613&view=sideways", "edge"),
    ("diff_bad_changed", "/compare?a=3612&b=3613&changed=maybe", "edge"),
]

# What a person opens in a browser: every page once (the tree alias duplicates the tree) plus one
# deliberate 404, so the error page is checked in both themes and both viewports too.
BROWSER_PAGES = [p for p in PAGES if p[2] == "page" and p[0] != "tree_alias"] + [
    ("versions_missing", "/versions/no/such/table", "edge"),
]
