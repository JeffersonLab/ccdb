"""Page views of the web GUI. Every view reads the database through `g.db`, the request's AlchemyProvider.

Endpoint names are referenced by the templates through url_for() and must stay as they are
(`directory_tree`, `versions`, `show_request`, `download_request`, ...).

Errors: a view calls abort(400, ...) or abort(404, ...) or lets the provider's ObjectIsNotFoundInDbError
propagate; errors.py renders the page. The two info fragments answer plain text instead, because the
tree loads them into a modal.
"""
import logging

import ccdb
from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.model import User, TypeTable, Variation
from ccdb.path_utils import parse_time
import json
import math
import re

from flask import g, render_template, url_for, request, redirect, make_response, abort
from sqlalchemy import select, text
from werkzeug.exceptions import HTTPException

from ccdb import ccdb_version
from ccdb.webgui import assignments, diff, queries
from ccdb.webgui.db import get_database

log = logging.getLogger("ccdb.webgui")

COMPARE_VIEWS = ("cells", "columns", "tables")
DATA_PAGE_SIZE = 200      # rows per page of a data table (assignment page, comparison); the list pages keep queries.DEFAULT_PAGE_SIZE
BIG_PAIR_CELLS = 20000    # a comparison above this many cells opens with the changed rows alone


def author_name(db, author_id):
    """The user name behind an author id; directories and tables store the id without a relationship."""
    user = db.session.get(User, author_id) if author_id is not None else None
    return user.name if user else ""


def link_args():
    """The current view's path and query arguments, ready to merge into a url_for() call.

    Keys starting with an underscore are dropped. url_for() reads `_external`, `_scheme`, `_anchor` and
    `_method` as its own control arguments, so a query string carrying one steers every link the page
    builds: `?_external=1` makes them absolute against the request's Host header, and `?_method=POST`
    fails the build and answers 500.
    """
    merged = {**request.view_args, **request.args.to_dict()}
    return {name: value for name, value in merged.items() if not name.startswith("_")}


def page_url(page_number):
    """URL of the current view with the same arguments and another page number; for the page navigation."""
    args = {**link_args(), "page": page_number}
    return url_for(request.endpoint, **args)


def switch_url(**changes):
    """URL of the current view with some arguments changed; a None value drops the argument (back to its default).
    Back to page 1, since a changed view or filter changes what the pages hold."""
    args = {**link_args(), **changes}
    args.pop("page", None)
    return url_for(request.endpoint, **{name: value for name, value in args.items() if value is not None})


def sort_url(column, current_sort, current_order):
    """URL that sorts by `column`; clicking the active column flips the order. Back to page 1."""
    order = "asc" if (column == current_sort and current_order == "desc") else "desc"
    if column != current_sort and column in ("variation", "author", "name", "action"):
        order = "asc"  # text columns read better ascending on the first click
    args = {**link_args(), "sort": column, "order": order}
    args.pop("page", None)
    return url_for(request.endpoint, **args)


TIME_ARGUMENT = re.compile(r"^\d{4}(-\d{2}(-\d{2}(_\d{2}(-\d{2}(-\d{2})?)?)?)?)?$")


def time_arg_or_400(text):
    """A time argument in the request-string form, `2020-01-04` or `2020-01-04_10-03-20`, or any leading part
    of it; a partial value means the end of that period, as in a request string. Empty → None; other text → 400."""
    text = (text or "").strip()
    if not text:
        return None
    if not TIME_ARGUMENT.match(text):
        abort(400, "'time' must look like 2020-01-04 or 2020-01-04_10-03-20, got '{0}'".format(text))
    return parse_time(text)


def affected_tree(db, grouped, variation_names):
    """The affected tables as a pruned directory tree: the root, the tables per directory id, the directory ids to
    keep (every ancestor of an affected table), and per table id the (variation, count, newest) badges in chain order."""
    root = db.get_root_directory()
    tables = db.session.execute(select(TypeTable).where(TypeTable.id.in_(list(grouped)))).scalars().all() if grouped else []
    tables_of, keep_dirs, badges = {}, set(), {}
    for table in sorted(tables, key=lambda each: each.name):
        table.parent_dir = db.dirs_by_id.get(table.parent_dir_id, root)
        tables_of.setdefault(table.parent_dir_id, []).append(table)
        directory = db.dirs_by_id.get(table.parent_dir_id)
        while directory is not None and directory.id not in keep_dirs:
            keep_dirs.add(directory.id)
            directory = db.dirs_by_id.get(directory.parent_id)
        badges[table.id] = [(name, *grouped[table.id][variation_id]) for variation_id, name in variation_names.items() if variation_id in grouped[table.id]]
    return dict(root=root, tables_of=tables_of, keep_dirs=keep_dirs, affected=badges)


def natural_key(name):
    """Sort key of a directory or table name: case-insensitive, digit runs as numbers (layer2 before layer10).

    The tree is rendered in this order and tree.js sorts by the same rule (compareNames); keep the two in step.
    re.split with a capturing group alternates text and digit chunks, text first, so two keys compare element
    by element without ever meeting a str against an int.
    """
    return [int(part) if i % 2 else part for i, part in enumerate(re.split(r"(\d+)", name.lower()))]


def by_name(items):
    """Directories or tables in natural name order: the Jinja filter the tree macros use."""
    return sorted(items, key=lambda item: natural_key(item.name))


def rows_page(rows):
    """One page of a data table's rows as (row index, row) pairs, from the request's `page` and `per_page`.

    The 12 largest production tables exceed 100 000 cells, so no data table is rendered whole. `per_page`
    snaps to PAGE_SIZES and `page` is clamped to the last page, as on the list pages.
    """
    page_number = queries.integer_arg(request.args, "page", default=1, minimum=1)
    wanted_size = queries.integer_arg(request.args, "per_page", default=DATA_PAGE_SIZE, minimum=1)
    per_page = min(queries.PAGE_SIZES, key=lambda size: abs(size - wanted_size))
    query = queries.PageQuery(page=min(page_number, max(1, math.ceil(len(rows) / per_page))), per_page=per_page)
    return queries.Page(items=list(enumerate(rows))[query.offset:query.offset + per_page], query=query, total=len(rows))


def page_window(page, width=2):
    """Page numbers to show around the current one; None marks a gap. Example: [1, None, 4, 5, 6, None, 72]."""
    numbers = sorted({1, page.pages} | {n for n in range(page.page - width, page.page + width + 1) if 1 <= n <= page.pages})
    with_gaps = []
    for number in numbers:
        if with_gaps and number - with_gaps[-1] > 1:
            with_gaps.append(None)
        with_gaps.append(number)
    return with_gaps


def wants_fragment():
    """True when the page script asks for the table alone (X-Fragment) or an HTMX client would (HX-Request)."""
    return request.headers.get("X-Fragment") == "1" or request.headers.get("HX-Request") == "true"


def table_page(page_template, fragment_template, **context):
    """The full page, or only the table fragment for a live-search request. Vary tells caches the two differ."""
    template = fragment_template if wants_fragment() else page_template
    response = make_response(render_template(template, **context))
    response.headers["Vary"] = "X-Fragment, HX-Request"
    return response


def register(app):
    """Adds every page view to the app with its original endpoint name."""
    app.jinja_env.globals.update(page_url=page_url, sort_url=sort_url, switch_url=switch_url, page_window=page_window,
                                 page_sizes=queries.PAGE_SIZES, INFINITE_RUN=queries.INFINITE_RUN)
    app.jinja_env.filters["by_name"] = by_name

    @app.route('/')
    @app.route('/tree')
    def directory_tree():
        db: ccdb.AlchemyProvider = g.db
        root_dir = db.get_root_directory()  # loads every directory in one query and builds the paths
        # One query for every table. Reading directory.type_tables per directory would lazy-load 65 times
        # on hallddb (F30). The tables get parent_dir from the cache so table.path is complete.
        tables_of = {}
        for table in db.session.execute(select(TypeTable).order_by(TypeTable.name)).scalars():
            table.parent_dir = db.dirs_by_id.get(table.parent_dir_id, root_dir)
            tables_of.setdefault(table.parent_dir_id, []).append(table)
        directory_count = len(db.dirs_by_id)
        table_count = sum(len(tables) for tables in tables_of.values())
        return render_template("tree.html", root=root_dir, tables_of=tables_of, directory_count=directory_count, table_count=table_count)

    @app.route('/get-dir-info/<int:dir_id>')
    def get_dir_info(dir_id):
        db: ccdb.AlchemyProvider = g.db
        try:
            directory = db.get_directory_by_id(dir_id)
        except ObjectIsNotFoundInDbError as error:
            return str(error), 404, {"Content-Type": "text/plain; charset=utf-8"}
        # Everything under the directory: the provider's directory cache gives the subtree without a query,
        # then one query lists the tables in it and two more count and date their assignments.
        directory_ids, pending = [], [directory]
        while pending:
            current = pending.pop()
            directory_ids.append(current.id)
            pending.extend(current.sub_dirs)
        table_ids = db.session.execute(select(TypeTable.id).where(TypeTable.parent_dir_id.in_(directory_ids))).scalars().all()
        return render_template('objects_dir_info.html', directory=directory, author_name=author_name(db, directory.author_id),
                               table_count=len(table_ids), activity=queries.assignment_activity(db.session, table_ids))

    @app.route('/get-table-info/<int:table_id>')
    def get_table_info(table_id):
        db: ccdb.AlchemyProvider = g.db
        try:
            table = db.get_type_table_by_id(table_id)
        except ObjectIsNotFoundInDbError as error:
            return str(error), 404, {"Content-Type": "text/plain; charset=utf-8"}
        return render_template('objects_table_info.html', table=table, author_name=author_name(db, table.author_id),
                               activity=queries.assignment_activity(db.session, [table.id]))

    @app.route('/vars')
    def variations():
        db: ccdb.AlchemyProvider = g.db
        query = queries.parse_page_query(request.args, queries.VARIATION_SORTS, default_sort="id", default_order="asc")
        page = queries.list_variations(db.session, query)
        return table_page("variations.html", "_variations_table.html", page=page, query=query, chains=queries.variation_chains(db.session))

    @app.route('/vars/compare')
    def compare_variations():
        """The tables that take their constants from a variation instead of the variations it inherits from.

        `variation` names it; `parent` is an ancestor to compare with (default: the direct parent): every table
        with an assignment in the chain segment from the parent (excluded) to the variation counts as affected.
        `run` and `time` narrow the assignments considered. Without `variation` the page shows the form alone.
        The root variation has no parent and gets no comparison: grouping its assignments is the one query
        that is slow on a production database.
        """
        db: ccdb.AlchemyProvider = g.db
        chains = queries.variation_chains(db.session)
        name = request.args.get("variation") or ""
        run = queries.run_arg(request.args, "run")
        time_text = (request.args.get("time") or "").strip()
        before = time_arg_or_400(time_text)
        context = dict(names=sorted(chains), name=name, run=run, time_text=time_text,
                       chain=[], ancestors=[], parent="", segment=[], affected=None, root=None, tables_of={}, keep_dirs=set())
        if name:
            if name not in chains:
                abort(404, "No variation named '{0}'".format(name))
            chain = chains[name]
            ancestors = chain[:-1]
            parent = request.args.get("parent") or (ancestors[-1] if ancestors else "")
            if ancestors and parent not in ancestors:
                abort(400, "'parent' must be a variation {0} inherits from ({1}), got '{2}'".format(name, ", ".join(ancestors), parent))
            segment = chain[chain.index(parent) + 1:] if ancestors else []
            context.update(chain=chain, ancestors=ancestors, parent=parent, segment=segment)
            if segment:
                ids = queries.variation_ids(db.session)
                variation_names = {ids[level]: level for level in segment}  # chain order, for the badges
                grouped = queries.affected_tables(db.session, variation_names, run=run, before=before)
                context.update(affected_tree(db, grouped, variation_names))
        return render_template("compare.html", **context)

    @app.route('/logs')
    def log_records():
        db: ccdb.AlchemyProvider = g.db
        # Sorted by id, not created: the two orders agree (ids grow with time) and only id has an index on the
        # production logs table — ORDER BY created costs 0.4 s over 820 000 rows on hallddb.
        query = queries.parse_page_query(request.args, queries.LOG_SORTS, default_sort="id")
        page = queries.list_logs(db.session, query)
        return table_page("logs.html", "_logs_table.html", page=page, query=query)

    def affected_links(db, record):
        """The Affected row of a log record: (label, url or None) per object, named as users know it.

        An assignment of a create or update record links by id without a lookup (a deleted one answers the 404
        page). A table, directory or variation is looked up and shown by its path or name with a link to its page;
        one that no longer exists keeps the record's own words (`table 850`). Users have no page. The directory
        cache is loaded only when a table or directory is named: it costs a query over all directories.
        """
        if any(kind in ("typeTables", "directories") for kind, _ in record.affected):
            db.get_root_directory()
        links = []
        for kind, object_id in record.affected:
            label, url = "{0} {1}".format({"typeTables": "table", "assignments": "assignment", "directories": "directory", "variations": "variation", "users": "user"}[kind], object_id), None
            if kind == "assignments" and record.action in ("create", "update"):
                url = url_for("show_request", assignment_id=object_id)
            elif kind == "typeTables":
                table = db.session.get(TypeTable, object_id)
                if table is not None and table.parent_dir_id in db.dirs_by_id:
                    table.parent_dir = db.dirs_by_id[table.parent_dir_id]
                    label, url = "table " + table.path, url_for("versions", table_path=table.path.lstrip("/"))
            elif kind == "directories":
                directory = db.dirs_by_id.get(object_id)
                if directory is not None:
                    label, url = "directory " + directory.path, url_for("directory_tree", filter=directory.path)
            elif kind == "variations":
                variation = db.session.get(Variation, object_id)
                if variation is not None:
                    label = "variation " + variation.name
                    url = url_for("compare_variations", variation=variation.name) if variation.parent_id else url_for("variations")
            links.append((label, url))
        return links

    @app.route('/logs/<int:log_id>')
    def log_record(log_id):
        """One log record in full: the list truncates comments, which reach 65 535 characters on the production database."""
        db: ccdb.AlchemyProvider = g.db
        record = queries.log_record(db.session, log_id)
        if record is None:
            abort(404, "No log record with id {0}".format(log_id))
        return render_template("log_record.html", record=record, affected=affected_links(db, record))

    @app.route('/doc')
    def documentation():
        return render_template("doc.html")

    @app.route('/health')
    def health():
        """Liveness and database check for load balancers and the container HEALTHCHECK: JSON, never cached."""
        try:
            engine = get_database(app).ensure_engine()
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            body, status = {"status": "ok", "database": "ok", "version": ccdb_version}, 200
        except Exception as error:  # a dead or wrong database must answer 503, not raise
            # The driver's message names the database host and the user it connected as. The route is
            # unauthenticated, so the answer stays a fixed string and the detail goes to the server log.
            log.warning("CCDB web GUI health check failed: %s", error)
            body, status = {"status": "error", "database": "unavailable", "version": ccdb_version}, 503
        return json.dumps(body), status, {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "no-store"}

    @app.route('/versions/<path:table_path>')
    def versions(table_path):
        db: ccdb.AlchemyProvider = g.db
        table = db.get_type_table("/" + table_path)  # unknown path → ObjectIsNotFoundInDbError → 404 page
        query = queries.parse_page_query(request.args, queries.ASSIGNMENT_SORTS, default_sort="created")
        filters = dict(variation=request.args.get("variation") or None,
                       run=queries.run_arg(request.args, "run"),
                       run_min=queries.run_arg(request.args, "run_min"),
                       run_max=queries.run_arg(request.args, "run_max"))
        page = queries.list_assignments(db.session, table, query, **filters)
        # The full page carries the table's info block (the rows of the tree's info modal) behind a Show info button;
        # the live-search fragment does not, so its two queries are skipped there.
        info = {} if wants_fragment() else dict(activity=queries.assignment_activity(db.session, [table.id]),
                                                author_name=author_name(db, table.author_id))
        return table_page("versions.html", "_versions_table.html", page=page, query=query, table=table, filters=filters,
                          variation_names=queries.table_variation_names(db.session, table), **info)

    @app.route('/test_request')
    def test_request():
        db: ccdb.AlchemyProvider = g.db
        db.get_root_directory()  # Loads directories
        tables = db.search_type_tables("*")
        variations = db.get_variations()
        return render_template("request.html", variations=variations, table_paths=sorted(table.path for table in tables))

    # ---------------------------------------------------------------- compare two assignments

    def resolve_side(db, text):
        """One side of a comparison: the Resolved assignment, or an (HTTP status, message) pair for the inline alert.

        A value made of digits only is a database id: parse_request() reads `1234` as a table path, so the
        choice is made here, before parsing. Anything else is a request string.
        """
        try:
            if text.isdigit():
                if int(text) > queries.INFINITE_RUN:  # the widest id the integer columns hold; wider ones raise in the driver
                    return None, (400, "'{0}' is not a database id".format(text))
                return assignments.resolve_assignment(db, assignment_id=int(text)), None
            return assignments.resolve_assignment(db, text), None
        except ObjectIsNotFoundInDbError as error:
            return None, (404, str(error))
        except HTTPException as error:  # resolve_assignment() aborts with 400 or 404
            return None, (error.code, error.description)

    def side_value(args, side, table_path):
        """What the URL says for side `a` or `b`: the side's own value, or the request string composed from the form's
        parts (`a_variation`, `a_run`, `a_time`) when at least one of them is filled."""
        value = (args.get(side) or "").strip()
        parts = {name: (args.get("{0}_{1}".format(side, name)) or "").strip() for name in ("variation", "run", "time")}
        if not value and table_path and any(parts.values()):
            value = assignments.compose_request({"path": table_path, **parts})
        return value

    @app.route('/compare')
    def compare_assignments():
        """The data of two assignments side by side.

        `a` and `b` name the sides (a request string or a database id each); which assignment is which is the
        user's choice, and the page never reorders them. The form sends `table` and the parts of each side; the
        view composes the request strings and redirects to the canonical `?a=…&b=…` URL, as show_request does
        with `path`. A side that does not resolve, or two sides from different tables, re-render the form with
        an inline alert and the matching 4xx status, so what the user typed stays on the page.
        """
        db: ccdb.AlchemyProvider = g.db
        args = request.args
        table_path = (args.get("table") or "").strip()
        sides = {side: side_value(args, side, table_path) for side in ("a", "b")}
        if table_path and sides["a"] and sides["b"] and (args.get("a") != sides["a"] or args.get("b") != sides["b"]):
            keep = {name: args[name] for name in ("view", "layout", "changed") if args.get(name)}
            return redirect(url_for("compare_assignments", a=sides["a"], b=sides["b"], **keep))

        errors, resolved, status = {}, {}, 200
        for side, value in sides.items():
            if not value:
                continue
            resolved[side], error = resolve_side(db, value)
            if error:
                errors[side] = error[1]
                status = 400 if 400 in (status, error[0]) else error[0]  # a malformed side (400) outranks a missing one (404)
                resolved.pop(side)
        table = None
        if table_path:
            try:
                table = db.get_type_table(table_path)
            except (ObjectIsNotFoundInDbError, ValueError):
                errors["table"] = "No table '{0}'".format(table_path)
                status = 400 if status == 400 else 404
        if len(resolved) == 2:
            table_a, table_b = (resolved[side].assignment.constant_set.type_table for side in ("a", "b"))
            if table_a.id != table_b.id:
                errors["table"] = "The sides belong to different tables: {0} and {1}. Compare assignments of one table.".format(table_a.path, table_b.path)
                status = 400
                resolved = {}
        if resolved and table is None and "table" not in errors:
            table = next(iter(resolved.values())).assignment.constant_set.type_table

        db.get_root_directory()  # loads directories, so every table path is complete
        context = dict(table=table, table_path=table.path if table else table_path, sides=sides, errors=errors, resolved=resolved,
                       table_paths=sorted(each.path for each in db.search_type_tables("*")),
                       variation_names=queries.table_variation_names(db.session, table) if table else sorted(queries.variation_ids(db.session)),
                       comparison=None)
        if len(resolved) == 2:
            context.update(comparison_context(resolved["a"].assignment, resolved["b"].assignment))
        return render_template("compare_assignments.html", **context), status

    def resolve_pair():
        """The two sides of a data route (`a` and `b` of the query string) as Resolved assignments of one table. A side
        that is empty, malformed or missing, and two sides from different tables, answer the error page with 400 or 404,
        as the other data routes do."""
        db: ccdb.AlchemyProvider = g.db
        resolved = {}
        for side in ("a", "b"):
            value = (request.args.get(side) or "").strip()
            if not value:
                abort(400, "The '{0}' parameter is empty. Expected a request string or a database id".format(side))
            resolved[side], error = resolve_side(db, value)
            if error:
                abort(error[0], error[1])
        a, b = resolved["a"].assignment, resolved["b"].assignment
        if a.constant_set.type_table.id != b.constant_set.type_table.id:
            abort(400, "The sides belong to different tables: {0} and {1}".format(a.constant_set.type_table.path, b.constant_set.type_table.path))
        return resolved["a"], resolved["b"]

    def pair_headers(resolved_a, resolved_b, content_type):
        """A pair of exact addresses (ids, or requests with a timestamp) may be cached for a day, as one exact address may."""
        exact = resolved_a.exact and resolved_b.exact
        return {"Content-Type": content_type, "Cache-Control": "public, max-age=86400" if exact else "no-cache"}

    @app.route('/compare/data.json')
    def compare_json():
        """The comparison as JSON: both sides' metadata, the columns, and the rows with the a and b value of every cell.
        A side that does not resolve answers the error page, as the other data routes do; `changed=1` keeps the rows with a change."""
        resolved_a, resolved_b = resolve_pair()
        a, b = resolved_a.assignment, resolved_b.assignment
        context = comparison_context(a, b)
        comparison = context["comparison"]
        body = {
            "table": a.constant_set.type_table.path,
            "columns": comparison.columns,
            "cells": comparison.cells,
            "changed_cells": comparison.changed_cells,
            "changed_rows": comparison.changed_rows,
            "changed_only": context["changed_only"],
            "rows": [{"row": row_i, "cells": [{"a": cell.a, "b": cell.b, "changed": cell.changed} for cell in cells]}
                     for row_i, cells in diff.kept_rows(comparison, context["changed_only"])],
        }
        for side, each in (("a", a), ("b", b)):
            body[side] = {key: value for key, value in assignments.assignment_dict(each).items() if key not in ("columns", "rows", "table")}
        return json.dumps(body, ensure_ascii=False, sort_keys=True, indent=1), 200, pair_headers(resolved_a, resolved_b, "application/json; charset=utf-8")

    @app.route('/compare/data.diff')
    def compare_diff():
        """The comparison as a unified diff (`diff -u`), the file every diff viewer opens: one line per row in the layout
        of the text download, so the diff of the two `data.txt` downloads and this file agree hunk for hunk. The headers
        name the sides by the request string each resolved to, then A or B, the id and the creation time after a tab.
        The whole table, whatever the page shows: `view`, `layout`, `changed` and `page` are ignored. Served as plain
        text, so a browser shows it; the page's link saves it under a `.diff` name through its `download` attribute."""
        resolved_a, resolved_b = resolve_pair()
        a, b = resolved_a.assignment, resolved_b.assignment
        table = a.constant_set.type_table
        columns = [{"name": column.name, "type": column.type} for column in table.columns]
        try:
            comparison = diff.diff_tables(a.constant_set.data_table, b.constant_set.data_table, columns)
        except ValueError as error:
            abort(400, "Cannot compare: {0}".format(error))
        labels = ["{0}, id {1}, created {2}".format(side, each.id, each.created) for side, each in (("A", a), ("B", b))]
        lines = diff.unified_diff(comparison, a.request, b.request, *labels)
        return "\n".join(lines) + "\n", 200, pair_headers(resolved_a, resolved_b, "text/plain; charset=utf-8")

    def comparison_context(a, b):
        """The diff of two assignments plus the view, layout, changed-only and paging parameters of the request."""
        table = a.constant_set.type_table
        columns = [{"name": column.name, "type": column.type} for column in table.columns]
        try:
            comparison = diff.diff_tables(a.constant_set.data_table, b.constant_set.data_table, columns)
        except ValueError as error:
            abort(400, "Cannot compare: {0}".format(error))
        view = request.args.get("view") or "cells"
        if view not in COMPARE_VIEWS:
            abort(400, "'view' must be one of {0}, got '{1}'".format(", ".join(COMPARE_VIEWS), view))
        layout = request.args.get("layout") or "auto"
        if layout not in assignments.LAYOUTS:
            abort(400, "'layout' must be one of {0}, got '{1}'".format(", ".join(assignments.LAYOUTS), layout))
        changed_arg = request.args.get("changed")
        if changed_arg not in (None, "", "0", "1"):
            abort(400, "'changed' must be 0 or 1, got '{0}'".format(changed_arg))
        # A pair above the cell budget opens with the changed rows alone: two 176 000-row sets rendered in full are a 50 MB page.
        changed_only = (comparison.cells > BIG_PAIR_CELLS) if changed_arg in (None, "") else changed_arg == "1"
        kept = diff.kept_rows(comparison, changed_only)
        page = rows_page([cells for _, cells in kept])
        page.items = [kept[row_i] for row_i, _ in page.items]  # the kept rows keep their true row index
        return dict(comparison=comparison, page=page, view=view, layout=layout, changed_only=changed_only,
                    column_lines=assignments.column_lines(layout, len(comparison.rows), len(columns)),
                    meta=side_meta(a, b), delta_text=diff.delta_text,
                    diff_file_name="{0}_{1}_{2}.diff".format(table.name, a.id, b.id))

    def side_meta(a, b):
        """The metadata rows of the comparison: (label, value of a, value of b, changed)."""
        rows = [("Variation", a.variation.name, b.variation.name),
                ("Run range", assignments.run_range_text(a), assignments.run_range_text(b)),
                ("Created", str(a.created), str(b.created)),
                ("Author", a.author.name if a.author else "", b.author.name if b.author else ""),
                ("Comment", a.comment, b.comment)]
        return [(label, value_a, value_b, value_a != value_b) for label, value_a, value_b in rows]

    # ---------------------------------------------------------------- assignments: page, JSON, text

    def data_headers(resolved, content_type):
        """Assignments are append-only, so an exact address (id, or request with a timestamp) may be cached for a day;
        a request without a timestamp resolves to the newest assignment and must be fetched again."""
        return {"Content-Type": content_type, "Cache-Control": "public, max-age=86400" if resolved.exact else "no-cache"}

    @app.route('/show_request')
    @app.route('/assignments/<int:assignment_id>')
    def show_request(assignment_id=None):
        db: ccdb.AlchemyProvider = g.db
        if assignment_id is None and not request.args.get('request') and request.args.get('path'):
            # The request form sends the parts; compose the request string and redirect to its canonical URL,
            # so the address bar shows the request string that scripts and the CLI understand.
            return redirect(url_for('show_request', request=assignments.compose_request(request.args)))
        layout = request.args.get("layout") or "auto"
        if layout not in assignments.LAYOUTS:
            abort(400, "'layout' must be one of {0}, got '{1}'".format(", ".join(assignments.LAYOUTS), layout))
        resolved = assignments.resolve_assignment(db, request.args.get('request', ''), assignment_id)
        assignment = resolved.assignment
        data = assignment.constant_set.data_table
        page = rows_page(data)
        # Page links address the assignment by its request string on both address forms (the byte-identity rule);
        # they keep the layout and page size only when the URL carries them.
        kept = {name: request.args[name] for name in ("layout", "per_page") if request.args.get(name)}
        return render_template("assignment.html",
                               assignment=assignment,
                               page=page,
                               page_href=lambda number: url_for("show_request", request=assignment.request, page=number, **kept),
                               previous=assignments.previous_assignment(db, assignment),
                               data=data,
                               layout=layout,
                               column_lines=assignments.column_lines(layout, len(data), len(assignment.constant_set.type_table.columns)),
                               variation=assignment.variation.name,
                               created=str(assignment.created),
                               author=assignment.author.name if assignment.author else "",
                               run_range=assignments.run_range_text(assignment),
                               comment=assignment.comment,
                               user_request_str=assignment.request)

    @app.route('/assignments/data.json')
    @app.route('/assignments/<int:assignment_id>/data.json')
    def assignment_json(assignment_id=None):
        db: ccdb.AlchemyProvider = g.db
        resolved = assignments.resolve_assignment(db, request.args.get('request', ''), assignment_id)
        body = json.dumps(assignments.assignment_dict(resolved.assignment), ensure_ascii=False, sort_keys=True, indent=1)
        return body, 200, data_headers(resolved, "application/json; charset=utf-8")

    @app.route('/assignments/data.txt')
    @app.route('/assignments/<int:assignment_id>/data.txt')
    def assignment_text(assignment_id=None):
        db: ccdb.AlchemyProvider = g.db
        resolved = assignments.resolve_assignment(db, request.args.get('request', ''), assignment_id)
        return assignments.assignment_text(resolved.assignment), 200, data_headers(resolved, "text/plain; charset=utf-8")

    @app.route('/dowload_request')
    @app.route('/download_request')
    def download_request():
        """The old text-dump entry points (one of them misspelled) redirect to the text view, so saved links keep working."""
        return redirect(url_for('assignment_text', request=request.args.get('request', '')))
