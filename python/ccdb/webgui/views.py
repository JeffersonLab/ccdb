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
from ccdb.model import User, TypeTable
from ccdb.path_utils import parse_time
import json
import re

from flask import g, render_template, url_for, request, redirect, make_response, abort
from sqlalchemy import select, text

from ccdb import ccdb_version
from ccdb.webgui import assignments, queries
from ccdb.webgui.db import get_database

log = logging.getLogger("ccdb.webgui")


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
    app.jinja_env.globals.update(page_url=page_url, sort_url=sort_url, page_window=page_window,
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
        return render_template("assignment.html",
                               assignment=assignment,
                               data=data,
                               layout=layout,
                               vertical=assignments.vertical_layout(layout, len(data), len(assignment.constant_set.type_table.columns)),
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
