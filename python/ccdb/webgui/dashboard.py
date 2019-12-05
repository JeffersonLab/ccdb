from flask import Blueprint
from flask import render_template


bp = Blueprint("dashboard", __name__, url_prefix='/d')


@bp.route("/")
def index():
    """Show all the posts, most recent first."""
    return render_template(
        "dash_base.html",
        app_name="Material Dashboard with Bokeh embedded in Flask",
        app_description="This Dashboard is served by a Bokeh server embedded in Flask.",
        app_icon="timeline"
    )

#    return render_template("data_timeline/index.html")

