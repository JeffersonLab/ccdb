
# -*- coding: utf-8 -*-
#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.


import os
import sys
import logging
import inspect

from .provider import AlchemyProvider
from .model import Variation, RunRange, Assignment, ConstantSet, Directory, TypeTable, TypeTableColumn
from .table_file import TextFileDOM, read_ccdb_text_file, read_namevalue_text_file
from .cmd.themes import NoColorTheme, ColoredTheme
from .brace_log_message import BraceMessage
from .cmd import themes
from . import path_utils

# the default ccdb logger
logger = logging.getLogger("ccdb")

INFINITE_RUN = 2147483647

if sys.version_info < (2, 7, 0):
    sys.stderr.write("You need python 2.7 or later to run CCDB\n")
    exit(1)


def get_ccdb_home_path():
    if "CCDB_HOME" in os.environ:
        return os.environ["CCDB_HOME"]

    this_dir = os.path.dirname(inspect.getfile(path_utils))
    this_dir = os.path.join(this_dir, "..", "..")
    this_dir = os.path.normpath(this_dir)
    return this_dir


def _check_dependent_libraries():
    """Checks if there are dependent libraries like SqlAlchemy"""

    def insert_ext_lib_in_python_path():
        """
        CCDB ships some external libraries in external_libs folder
        if CCDB is cloned from GitHub we can load them
        if CCDB is installed from pip, dependendencies should be installed too
        """
        ext_lib_dir = os.path.join(get_ccdb_home_path(), 'python', 'external_libs')
        if os.path.isdir(ext_lib_dir):
            logger.debug("Found 'ext_lib_dir' = '{}'. Adding to PYTHONPATH...".format(ext_lib_dir))
            sys.path.append(ext_lib_dir)
        else:
            logger.debug("No 'ext_lib_dir' = '{}' is found (or has the right permission)".format(ext_lib_dir))
            print("Not all ccdb core dependencies have been found")
            print("Please make sure, that SqlALchemy, pymysql and six are installed")
            print("run 'ccdb --debug' for info on what exact dependency is missing")
            exit(1)

    def log_lib_not_found(libname):
        logger.debug(libname + " is not found. Trying to load embedded one (will not work if CCDB installed by PIP")

    try:
        import sqlalchemy
    except:
        log_lib_not_found('sqlalchemy')
        insert_ext_lib_in_python_path()

    try:
        import six
    except:
        log_lib_not_found('six')
        insert_ext_lib_in_python_path()

    try:
        import pymysql
    except:
        log_lib_not_found('pymysql')
        insert_ext_lib_in_python_path()


def init_ccdb_console():
    from .cmd import ConsoleContext
    import ccdb.cmd.colorama

    # SETUP LOGGER
    # ------------------------------

    # create and set console handler
    stdout_handler = logging.StreamHandler()
    stdout_handler.stream = sys.stdout
    logger.addHandler(stdout_handler)

    # create stderr handler
    stderr_handler = logging.StreamHandler()
    stderr_handler.stream = sys.stderr
    stderr_handler.setLevel(logging.ERROR)
    logger.addHandler(stderr_handler)

    # Logger level from arguments
    if "-s" in sys.argv or "--silent" in sys.argv:
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.INFO)

    # Should we load external libraries?
    _check_dependent_libraries()

    # create console context
    context = ConsoleContext()

    # CHECK SOME COMMAND LINE KEYS
    # ------------------------------
    if "-h" in sys.argv or "--help" in sys.argv:
        print("Please call 'ccdb help' for help")

    cmd.colorama.init(autoreset=True)

    if "--no-color" in sys.argv:
        # no colors for output
        context.theme = NoColorTheme()
    else:
        # colors are ON
        context.theme = ColoredTheme()

    if "--debug" in sys.argv:
        logger.setLevel(logging.DEBUG)
        logger.debug("debugging verbose mode is " + context.theme.Ok + " ON " + context.theme.Reset)

    if "--raise" in sys.argv:
        logger.debug("--raise flag found. The process will raise exceptions thrown by commands"
                     " instead of humble notifications and non 0 return result")
        context.silent_exceptions = False

    # CONNECTION STRING
    # ------------------------------

    # this is default connection string (for a fallback)
    context.connection_string = "mysql://ccdb_user@localhost/ccdb"

    # connection string
    if "CCDB_CONNECTION" in list(os.environ.keys()):
        context.connection_string = os.environ["CCDB_CONNECTION"]
        logger.debug("Set connection string from $CCDB_CONNECTION :" + context.connection_string)
    else:
        # fallback to jana calib url
        if "JANA_CALIB_URL" in list(os.environ.keys()):
            jana_url = os.environ["JANA_CALIB_URL"]
            logger.debug("$CCDB_CONNECTION was not found. Found JANA_CALIB_URL ('"+jana_url+"'). Try use it")

            if jana_url.startswith("mysql://") or jana_url.startswith("sqlite://"):
                context.connection_string = jana_url
            else:
                logger.debug("JANA_CALIB_URL does not starts with mysql:// or sqlite://. Skipped")

    # connection string in in command line arguments ( by -c or --connection) is processed by context.process(sys.argv)

    if "CCDB_USER" in list(os.environ.keys()):
        context.user_name = os.environ["CCDB_USER"]
        logger.debug("Set user name from $CCDB_USER :" + context.user_name)

    # START PROCESSING
    # ------------------------------

    # initialize console context
    context.register_utilities()

    # start processor
    result = context.process(sys.argv)
    if result is None:                      # The result must be something! (even true)
        sys.exit(1)
