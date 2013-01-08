#config file for ccdb cgi scripts


#database connection string. connection string might be in form:
# mysql://<username>:<password>@<mysql.address>:<port> <database>
# sqlite:///path/to/file.sqlite
# example:
#   connection_string = "mysql://ccdb_user@hallddb.jlab.org/ccdb"
connection_string = "mysql://ccdb_user@hallddb.jlab.org/ccdb"


# if CCDB/python directory is not in PYTHONPATH env. variable of the server,
# this setting forces python to look for ccdb modules in folder set  by 'ccdb_python_path'
# example:
#   force_import_ccdb_python = True
force_import_ccdb_python = True


# Path for python to search CCDB modules in.
# Should be an absolute path for $CCDB_HOME/python directory
# This setting is relevant only if force_import_ccdb_python = True
# example:
#  ccdb_python_path = "/home/romanov/halld/ccdb/trunk/python"
ccdb_python_path = "/home/romanov/halld/ccdb/trunk/python"


# the path to css, js, image directories.
# example: 
#   if css, js, and image parts are in https://halldweb1.jlab.org/ccdb/
#   site root might be: 
#     site_root = "/ccdb"
#   or 
#     site_root = "https://halldweb1.jlab.org/ccdb/"
site_root = ""


# same as site_root but for cgi directory where all python scripts are
# example:
#   site_cgi_root = "/cgi-bin"
site_cgi_root = "/cgi-bin"


# url of the site without subdirectories
# example: 
#   site_url = "https://halldweb1.jlab.org"
site_url = "http://127.0.0.1/"


# cgitb is a python module which is capable of displaying python errors to browser
# leave it True for debugging reasons. Or False for production environment
# example: 
#   cgitb_is_enabled = True
cgitb_is_enabled = True







#-------------- end of configuration file -------------------------


def python_config():
    """
    setup python environment for running website

    :return: None
    """

    # force to add ccdb_python_path
    if force_import_ccdb_python:
        import sys
        sys.path.append(ccdb_python_path)

    #displaying python errors to browser
    if cgitb_is_enabled:
        import cgitb
        cgitb.enable()


