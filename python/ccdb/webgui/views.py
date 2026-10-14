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

from flask import g, render_template, url_for, request, redirect
from markupsafe import Markup

from ccdb.webgui import assignments, queries


def dir_to_ul(directory, level=0):
    """The directory tree as nested <ul> markup, for directory_tree.html.

    Names and paths come from the database and go through Markup.format(), which escapes them:
    a table called `<script>` must show as text, not run or swallow the rest of the page.

    :type directory: ccdb.model.Directory
    :rtype: markupsafe.Markup
    """
    if not len(directory.sub_dirs) and not len(directory.type_tables):
        return Markup("<ul></ul>")

    result = Markup("<ul>\n")
    for sub_dir in directory.sub_dirs:
        assert isinstance(sub_dir, Directory)
        result += Markup('<li data="{path}" class="directory"><i class="indicator bi bi-folder"></i>'
                         '<span class="clickable">{name}</span><button onclick="showInfo(this.dataset.url)" data-url="{url}">&#128712;</button>'
                         ).format(path=sub_dir.path, name=sub_dir.name, url=url_for('get_dir_info', dir_id=sub_dir.id))
        result += dir_to_ul(sub_dir, level + 1)
        result += Markup("</li>\n")

    for table in directory.type_tables:
        assert isinstance(table, TypeTable)
        result += Markup('<li data="{path}"><i class="indicator bi bi-table"></i><a class="clickable" href="{url}">{name}</a> '
                         '<button onclick="showInfo(this.dataset.url)" data-url="{info_url}">&#128712;</button></li>\n'
                         ).format(path=table.path, url=url_for('versions', table_path=table.path.lstrip('/')), name=table.name,
                                  info_url=url_for('get_table_info', table_id=table.id))

    result += Markup("</ul>\n")
    return result


def author_name(db, author_id):
    """The user name behind an author id; directories and tables store the id without a relationship."""
    user = db.session.get(User, author_id) if author_id is not None else None
    return user.name if user else ""


def page_url(page_number):
    """URL of the current view with the same arguments and another page number; for the page navigation."""
    args = {**request.view_args, **request.args.to_dict(), "page": page_number}
    return url_for(request.endpoint, **args)


def register(app):
    """Adds every page view to the app with its original endpoint name."""
    app.jinja_env.globals["page_url"] = page_url

    @app.route("/hello")
    def hello():
        return "Hello, World!"

    @app.route('/dirs')
    def directories():
        db: ccdb.AlchemyProvider = g.db
        db.get_root_directory()
        return render_template("direcotires.html", dirs_by_path=db.dirs_by_path)

    @app.route('/')
    @app.route('/tree')
    def directory_tree():
        db: ccdb.AlchemyProvider = g.db
        root_dir = db.get_root_directory()
        html_tree = dir_to_ul(root_dir, level=0)
        return render_template("directory_tree.html", html_tree=html_tree, dirs_by_path=db.dirs_by_path)

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
        return render_template("variations.html", page=page)

    @app.route('/logs')
    def log_records():
        db: ccdb.AlchemyProvider = g.db
        # Sorted by id, not created: the two orders agree (ids grow with time) and only id has an index on the
        # production logs table — ORDER BY created costs 0.4 s over 820 000 rows on hallddb.
        query = queries.parse_page_query(request.args, queries.LOG_SORTS, default_sort="id")
        page = queries.list_logs(db.session, query)
        return render_template("logs.html", page=page)

    @app.route('/doc')
    def documentation():
        return render_template("doc.html")

    @app.route('/versions/<path:table_path>')
    def versions(table_path):
        db: ccdb.AlchemyProvider = g.db
        table = db.get_type_table("/" + table_path)  # unknown path → ObjectIsNotFoundInDbError → 404 page
        query = queries.parse_page_query(request.args, queries.ASSIGNMENT_SORTS, default_sort="created")
        page = queries.list_assignments(
            db.session, table, query,
            variation=request.args.get("variation") or None,
            run=queries.integer_arg(request.args, "run", minimum=0),
            run_min=queries.integer_arg(request.args, "run_min", minimum=0),
            run_max=queries.integer_arg(request.args, "run_max", minimum=0))
        return render_template("versions.html", page=page, table=table, table_path=table_path)

    @app.route('/test_request')
    def test_request():
        db: ccdb.AlchemyProvider = g.db
        db.get_root_directory()  # Loads directories
        tables = db.search_type_tables("*")
        variations = db.get_variations()
        return render_template("test_request.html", variations=variations, tables=tables,
                               table_paths=[table.path for table in tables])

    # ---------------------------------------------------------------- assignments: page, JSON, text

    def data_headers(resolved, content_type):
        """Assignments are append-only, so an exact address (id, or request with a timestamp) may be cached for a day;
        a request without a timestamp resolves to the newest assignment and must be fetched again."""
        return {"Content-Type": content_type, "Cache-Control": "public, max-age=86400" if resolved.exact else "no-cache"}

    @app.route('/show_request', methods=['GET', 'POST'])
    @app.route('/assignments/<int:assignment_id>')
    def show_request(assignment_id=None):
        db: ccdb.AlchemyProvider = g.db
        resolved = assignments.resolve_assignment(db, request.args.get('request', ''), assignment_id)
        assignment = resolved.assignment
        return render_template("show_request.html",
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
