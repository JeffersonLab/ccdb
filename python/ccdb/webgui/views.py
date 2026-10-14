"""Page views of the web GUI. Every view reads the database through `g.db`, the request's AlchemyProvider.

Endpoint names are referenced by the templates through url_for() and must stay as they are
(`directory_tree`, `versions`, `show_request`, `download_request`, ...).

Errors: a view calls abort(400, ...) or abort(404, ...) or lets the provider's ObjectIsNotFoundInDbError
propagate; errors.py renders the page. The two info fragments answer plain text instead, because the
tree loads them into a modal.
"""
import ccdb
from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.model import User, TypeTable, Directory
import json

from flask import g, render_template, url_for, request, redirect, make_response
from sqlalchemy import select

from ccdb.webgui import assignments, queries


def author_name(db, author_id):
    """The user name behind an author id; directories and tables store the id without a relationship."""
    user = db.session.get(User, author_id) if author_id is not None else None
    return user.name if user else ""


def page_url(page_number):
    """URL of the current view with the same arguments and another page number; for the page navigation."""
    args = {**request.view_args, **request.args.to_dict(), "page": page_number}
    return url_for(request.endpoint, **args)


def sort_url(column, current_sort, current_order):
    """URL that sorts by `column`; clicking the active column flips the order. Back to page 1."""
    order = "asc" if (column == current_sort and current_order == "desc") else "desc"
    if column != current_sort and column in ("variation", "author", "name", "action"):
        order = "asc"  # text columns read better ascending on the first click
    args = {**request.view_args, **request.args.to_dict(), "sort": column, "order": order}
    args.pop("page", None)
    return url_for(request.endpoint, **args)


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
        return render_template('objects_dir_info.html', directory=directory, author_name=author_name(db, directory.author_id))

    @app.route('/get-table-info/<int:table_id>')
    def get_table_info(table_id):
        db: ccdb.AlchemyProvider = g.db
        try:
            table = db.get_type_table_by_id(table_id)
        except ObjectIsNotFoundInDbError as error:
            return str(error), 404, {"Content-Type": "text/plain; charset=utf-8"}
        return render_template('objects_table_info.html', table=table, author_name=author_name(db, table.author_id))

    @app.route('/vars')
    def variations():
        db: ccdb.AlchemyProvider = g.db
        query = queries.parse_page_query(request.args, queries.VARIATION_SORTS, default_sort="id", default_order="asc")
        page = queries.list_variations(db.session, query)
        return table_page("variations.html", "_variations_table.html", page=page, query=query, chains=queries.variation_chains(db.session))

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

    @app.route('/versions/<path:table_path>')
    def versions(table_path):
        db: ccdb.AlchemyProvider = g.db
        table = db.get_type_table("/" + table_path)  # unknown path → ObjectIsNotFoundInDbError → 404 page
        query = queries.parse_page_query(request.args, queries.ASSIGNMENT_SORTS, default_sort="created")
        filters = dict(variation=request.args.get("variation") or None,
                       run=queries.integer_arg(request.args, "run", minimum=0),
                       run_min=queries.integer_arg(request.args, "run_min", minimum=0),
                       run_max=queries.integer_arg(request.args, "run_max", minimum=0))
        page = queries.list_assignments(db.session, table, query, **filters)
        return table_page("versions.html", "_versions_table.html", page=page, query=query, table=table, filters=filters,
                          variation_names=queries.table_variation_names(db.session, table))

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

    @app.route('/show_request', methods=['GET', 'POST'])
    @app.route('/assignments/<int:assignment_id>')
    def show_request(assignment_id=None):
        db: ccdb.AlchemyProvider = g.db
        if assignment_id is None and not request.args.get('request') and request.args.get('path'):
            # The request form sends the parts; compose the request string and redirect to its canonical URL,
            # so the address bar shows the request string that scripts and the CLI understand.
            return redirect(url_for('show_request', request=assignments.compose_request(request.args)))
        resolved = assignments.resolve_assignment(db, request.args.get('request', ''), assignment_id)
        assignment = resolved.assignment
        return render_template("assignment.html",
                               assignment=assignment,
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
