#config file for ccdb cgi scripts


#database connection string. connection string might be in form:
# mysql://<username>:<password>@<mysql.address>:<port> <database>
# sqlite:///path/to/file.sqlite
connection_string = "mysql://ccdb_user@halldweb1/ccdb"


# if ccdb/python directory is not in PYTHONPATH this setting will force
# to add ccdb_python_path to python modules search path when python_config() is called
force_import_ccdb_python = False


# Path of the ccdb/python directory.
# This setting is relevant only if force_import_ccdb_python = True
ccdb_python_path = "/home/romanov/halld/ccdb/trunk/python"


# cgitb is a python module which is capable of displaying python errors to browser
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


