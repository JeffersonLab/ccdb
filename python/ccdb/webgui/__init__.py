import os
import ccdb
from ccdb.model import User, TypeTable
from ccdb.path_utils import parse_request, ParseRequestResult
from flask import Flask, g, render_template, url_for, jsonify

from ccdb.model import Directory
from ccdb.errors import ObjectIsNotFoundInDbError


def print_app_functions(app):
    print("APPLICATION VIEW FUNCTIONS:")
    print("====================================")
    for name, func in app.view_functions.items():
        print(f"{name:<15}: {func}")

    print("====================================")
    print()


def dir_to_ul(directory, level=0):
    """
    :param directory: Directory
    :type directory: ccdb.model.Directory
    :param level: level of the recursion
    :return: String
    :rtype; str
    """

    opened_class = 'bi-folder2-open'
    closed_class = 'bi-folder'
    file_class = 'bi-table'

    if not len(directory.sub_dirs) and not len(directory.type_tables):
        return "<ul></ul>"

    result = '<ul>\n'
    for sub_dir in directory.sub_dirs:
        assert isinstance(sub_dir, Directory)
        result += f'<li data="{sub_dir.path}" class="directory"><i class="indicator bi {closed_class}"></i><span class="clickable">{sub_dir.name}</span><button onclick="showDirInfo({sub_dir.id})">&#128712;</button>'
        result += dir_to_ul(sub_dir, level + 1)
        result += '</li>\n'

    for table in directory.type_tables:
        assert isinstance(table, TypeTable)
        table_url = url_for('versions', table_path=table.path)
        result += f'<li data="{table.path}"><i class="indicator bi {file_class}"></i><a class="clickable" href="{table_url}">{table.name}</a> <button onclick="showTableInfo({table.id})">&#128712;</button></li>\n'

    result += '</ul>\n'
    return result


def cerate_ccdb_flask_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        #SQL_CONNECTION_STRING="mysql://ccdb_user@hallddb.jlab.org/ccdb2"
        SQL_CONNECTION_STRING = os.getenv(
            "SQL_CONNECTION_STRING",
            "mysql://test_user:test_user_password@localhost:3306/test_ccdb"
        )
    )

    @app.before_request
    def before_request():
        """This function is called in the beginning of requests"""
        # Connect to CCDB
        g.db = ccdb.AlchemyProvider()
        g.db.connect(app.config["SQL_CONNECTION_STRING"])

    @app.teardown_request
    def teardown_request(exception):
        """This function is called in the end of each request"""

        # Try to get CCDB connectino and close it
        db = getattr(g, 'db', None)
        if db:
            db.disconnect()

    @app.route("/hello")
    def hello():
        return "Hello, World!"

    @app.route('/dirs')
    def directories():
        # Get ccdb Alchemy provider from flask global state 'g'
        db: ccdb.AlchemyProvider = g.db

        # This will make ccdb to get direcotries from db
        db.get_root_directory()

        # Render a template with the directories
        return render_template("direcotires.html", dirs_by_path=db.dirs_by_path)

    # @app.route('/')
    # def index():
    #     return render_template(
    #         "dash_base.html",
    #         app_name="Material Dashboard with Bokeh embedded in Flask",
    #         app_description="This Dashboard is served by a Bokeh server embedded in Flask.",
    #         app_icon="timeline"
    #     )

    @app.route('/')
    @app.route('/tree')
    def directory_tree():
        # Get ccdb Alchemy provider from flask global state 'g'
        db: ccdb.AlchemyProvider = g.db

        # This will make ccdb to get directories from db
        root_dir = db.get_root_directory()

        # Generate html code of directory tree
        html_tree = dir_to_ul(root_dir, level=0)

        return render_template("directory_tree.html", html_tree=html_tree, dirs_by_path=db.dirs_by_path)

    @app.route('/get-dir-info/<int:dir_id>')
    def get_dir_info(dir_id):
        db: ccdb.AlchemyProvider = g.db
        db._ensure_dirs_loaded()
        directory = db.get_directory_by_id(dir_id)
        if not directory:
            return jsonify({"error": "Directory not found"}), 404
        return render_template('objects_dir_info.html', directory=directory)

    @app.route('/get-table-info/<int:table_id>')
    def get_table_info(table_id):
        db: ccdb.AlchemyProvider = g.db
        db._ensure_dirs_loaded()
        table = db.get_type_table_by_id(table_id)
        if not table:
            return jsonify({"error": "Table not found"}), 404
        return render_template('objects_table_info.html', table=table)

    @app.route('/vars')
    def variations():
        # Get ccdb Alchemy provider from flask global state 'g'
        db: ccdb.AlchemyProvider = g.db

        variations = db.get_variations()

        return render_template("variations.html", variations=variations)

    @app.route('/logs')
    def log_records():
        # Get ccdb Alchemy provider from flask global state 'g'
        db: ccdb.AlchemyProvider = g.db

        records = db.get_log_records(1000)

        return render_template("logs.html", records=records)

    @app.route('/doc')
    def documentation():
        return render_template("doc.html")

    @app.route('/versions/<path:table_path>')
    def versions(table_path):

        # Get ccdb Alchemy provider from flask global state 'g'
        db: ccdb.AlchemyProvider = g.db

        try:
            if table_path:
                assignments = db.get_assignments("/" + table_path)
                if not assignments:
                    return render_template("error.html", message="No assignments found for this table path.",
                                           table_path=table_path), 404
            else:
                return render_template("error.html", message="No table path provided.", table_path=table_path), 404
        except ccdb.errors.ObjectIsNotFoundInDbError as e:
            return render_template("error.html", message=str(e), table_path=table_path), 404

        return render_template("versions.html", assignments=assignments, table_path=table_path)

    @app.route('/test_request')
    def test_request():
        db: ccdb.AlchemyProvider = g.db

        db.get_root_directory()  # Loads directories

        tables = db.search_type_tables("*")

        tables_autocomplete = '[' + ','.join(['"' + table.path + '"' for table in tables]) + ']'
        variations = db.get_variations()

        return render_template("test_request.html", variations=variations, tables=tables,
                               tables_autocomplete=tables_autocomplete)

    @app.route('/show_request', methods=['GET', 'POST'])
    def show_request():
        from flask import request

        db: ccdb.AlchemyProvider = g.db
        # return str(request.form["request"])

        str_request = request.args.get('request', '')

        if not str_request:
            return "Error empty request"

        assignment = None  # this is the desired assignment
        variation = ""
        created = ""
        author = ""
        run_range = ""
        comment = ""

        # parse request and prepare time
        request = parse_request(str_request)
        assert isinstance(request, ParseRequestResult)
        time = request.time if request.time_is_parsed else None

        # query database for assignments for this request
        try:
            assignments = db.get_assignments(request.path, request.run, request.variation, time)
        except ccdb.errors.ObjectIsNotFoundInDbError:
            return "Something is not found in the DB"

        # get first assignment
        if assignments and len(assignments) != 0:
            assignment = assignments[0]
            assert (isinstance(assignment, ccdb.Assignment))

            variation = assignment.variation.name
            created = str(assignment.created)
            run_range = str(assignment.run_range.min) + " - "
            run_range = run_range + (
                str(assignment.run_range.max) if assignment.run_range.max != 2147483647 else "inf.")
            comment = assignment.comment.replace("\n", "<br />")
        try:
            author = db.session.query(User).filter(User.id == assignment.author_id).one().name
        except Exception as ex:
            print(ex)

        return render_template("show_request.html",
                               assignment=assignment,
                               variation=variation,
                               created=created,
                               author=author,
                               run_range=run_range,
                               comment=comment,
                               user_request_str=str_request
                               )

    @app.route('/dowload_request')
    def download_request():
        from flask import request

        db: ccdb.AlchemyProvider = g.db
        # return str(request.form["request"])

        str_request = request.args.get('request', '')

        if str_request:

            # parse request and prepare time
            request = parse_request(str_request)
            assert isinstance(request, ParseRequestResult)
            time = request.time if request.time_is_parsed else None

            # query database for assignments for this request
            assignments = db.get_assignments(request.path, request.run, request.variation, time)

            # get first assignment
            if not assignments or len(assignments) == 0:
                return "No assignments found"

            assignment = assignments[0]
            assert (isinstance(assignment, ccdb.Assignment))
            result = " "
            # print META information about the request
            result += f"#meta full request: {assignment.request}\n<br>"
            result += f"#meta variation: {assignment.variation.name}\n<br>"
            result += f"#meta created: {assignment.created}\n<br>"
            max_run = assignment.run_range.max if assignment.run_range.max != 2147483647 else "inf."
            result += f"#meta run range: {assignment.run_range.min} - {max_run}<br>"
            try:
                result += f"#meta author:  {db.session.query(User).filter(User.id == assignment.author_id).one().name}<br>"  # TODO make provider proper function to handl author by id
            except Exception as ex:
                result += f"#meta author: error getting name by id = {assignment.author_id}<br>"

            # print comment
            result += "<br>\n#" + assignment.comment.replace("\n", "\n#") + "\n\n<br><br>"

            # column names
            result += "#& ".join([column.name for column in assignment.constant_set.type_table.columns]) + "<br>"

            # print
            for row in assignment.constant_set.data_table:
                result += " ".join(row) + "<br>"

            return result

    # THIS IS FOR FUTURE
    # ====================================================================
    # from ccdb.webgui.data_timeline import bp as time_line_bp
    # from ccdb.webgui.dashboard import bp as dashboard_bp
    #
    # app.register_blueprint(time_line_bp)
    # app.register_blueprint(dashboard_bp)
    #
    # # make url_for('index') == url_for('blog.index')
    # # in another app, you might define a separate main index here with
    # # app.route, while giving the blog blueprint a url_prefix, but for
    # # the tutorial the blog will be the main index
    # app.add_url_rule("/", endpoint="index")
    # ====================================================================

    print_app_functions(app)

    return app


if __name__ == '__main__':
    cerate_ccdb_flask_app().run()
