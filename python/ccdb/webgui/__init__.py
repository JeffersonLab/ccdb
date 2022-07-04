import cgi
import os

from flask import Flask, g, render_template

import ccdb
from ccdb import provider
from ccdb.path_utils import parse_request, ParseRequestResult


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

    if not len(directory.sub_dirs) and not len(directory.type_tables):
        return ""

    spaces = level * "  "
    result = f"{spaces}<!-- {directory.name} -->\n" \
             f"{spaces}<ul>\n"

    # print subdirectories
    for sub_dir in directory.sub_dirs:
        result += f'{spaces}  <li> <strong>{directory.name}</strong> \n' \
                  f'{dir_to_ul(sub_dir, level + 1)} \n' \
                  f'{spaces}  </li>\n'

    # print type tables
    for table in directory.type_tables:
        result += f'{spaces}  <li> {table.name} </li> \n'

    # close
    result += f"{spaces}</ul>\n"
    return result


def cerate_ccdb_flask_app(test_config=None):
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        # a default secret that should be overridden by instance config
        SQL_CONNECTION_STRING="mysql://ccdb_user@localhost/ccdb"
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
        return render_template("simple_direcotires.html", dirs_by_path=db.dirs_by_path)

    @app.route('/')
    def index():
        return render_template(
            "dash_base.html",
            app_name="Material Dashboard with Bokeh embedded in Flask",
            app_description="This Dashboard is served by a Bokeh server embedded in Flask.",
            app_icon="timeline"
        )

    @app.route('/simple')
    def simple():
        return render_template("simple.html")

    @app.route('/tree')
    def directory_tree():
        # Get ccdb Alchemy provider from flask global state 'g'
        db: ccdb.AlchemyProvider = g.db

        # This will make ccdb to get directories from db
        root_dir = db.get_root_directory()

        # Generate html code of directory tree
        html_tree = dir_to_ul(root_dir, level=0)

        return render_template("simple_tree.html", html_tree=html_tree)

    @app.route('/vars')
    def variations_test():
        # Get ccdb Alchemy provider from flask global state 'g'
        db: ccdb.AlchemyProvider = g.db

        variations = db.get_variations()

        return render_template("variations.html", variations=variations)

    @app.route('/logs')
    def log_records():
        # Get ccdb Alchemy provider from flask global state 'g'
        db: ccdb.AlchemyProvider = g.db

        records = db.get_log_records(100)

        return render_template("simple_logs.html", records=records)

    @app.route('/versions/<path:table_path>')
    def versions(table_path):

        # Get ccdb Alchemy provider from flask global state 'g'
        db: ccdb.AlchemyProvider = g.db

        if table_path:
            assignments = db.get_assignments("/"+table_path)  # "/test/test_vars/test_table"
        else:
            assignments = None

        return render_template("simple_versions.html", assignments=assignments, table_path=table_path)

    @app.route('/test_request')
    def test_request():
        db: ccdb.AlchemyProvider = g.db

        db.get_root_directory()  # Loads directories

        tables = db.search_type_tables("*")

        tables_autocomplete = '[' + ','.join(['"' + table.path + '"' for table in tables]) + ']'
        variations = db.get_variations()

        return render_template("test_request.html", variations=variations, tables=tables, tables_autocomplete=tables_autocomplete)

    @app.route('/show_request')
    def show_request():
        from flask import request

        db: ccdb.AlchemyProvider = g.db

        assignment = None  # this is the desired assignment
        variation = ""
        created = ""
        author = ""
        run_range = ""
        comment = ""

        # get request from web form
        str_request = request.args.get('key', '')
        # str_request = "/test/test_vars/test_table:0:default:2012-10-30_23-48-41"

        if str_request:

            # parse request and prepare time
            request = parse_request(str_request)
            assert isinstance(request, ParseRequestResult)
            time = request.time if request.time_is_parsed else None

            # query database for assignments for this request
            assignments = db.get_assignments(request.path, request.run, request.variation, time)

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
