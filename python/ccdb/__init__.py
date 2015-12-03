
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

#the default ccdb logger
logger = logging.getLogger("ccdb")

INFINITE_RUN = 2147483647

def get_ccdb_home_path():
    if "CCDB_HOME" in os.environ:
        return os.environ["CCDB_HOME"]

    this_dir = os.path.dirname(inspect.getfile(path_utils))
    this_dir = os.path.join(this_dir, "..","..")
    this_dir = os.path.normpath(this_dir)
    return this_dir

def init_ccdb_console():
    from .cmd import ConsoleContext
    import cmd.colorama

    # TODO move ccdb to pure logging. NO print command at all

    # create logger
    logger = logging.getLogger("ccdb")

    # create and set console handler
    ch = logging.StreamHandler()
    ch.stream = sys.stdout

    logger.addHandler(ch)

    # create console context
    context = ConsoleContext()

    # CHECK SOME COMMAND LINE KEYS
    # ------------------------------
    if "-h" in sys.argv or "--help" in sys.argv:
        print("Please call 'ccdb help' for help")

    if "-s" in sys.argv or "--silent" in sys.argv:
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.INFO)

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
    if "CCDB_CONNECTION" in os.environ.keys():
        context.connection_string = os.environ["CCDB_CONNECTION"]
        logger.debug("Set connection string from $CCDB_CONNECTION :" + context.connection_string)
    else:
        # fallback to jana calib url
        if "JANA_CALIB_URL" in os.environ.keys():
            jana_url = os.environ["JANA_CALIB_URL"]
            logger.debug("$CCDB_CONNECTION was not found. Found JANA_CALIB_URL ('"+jana_url+"'). Try use it")

            if jana_url.startswith("mysql://") or jana_url.startswith("sqlite://"):
                context.connection_string = jana_url
            else:
                logger.debug("JANA_CALIB_URL does not starts with mysql:// or sqlite://. Skipped")



    # connection string in in command line arguments ( by -c or --connection) is processed by context.process(sys.argv)

    if "CCDB_USER" in os.environ.keys():
        context.user_name = os.environ["CCDB_USER"]
        logger.debug("Set user name from $CCDB_USER :" + context.user_name)
    # elif "USER" in os.environ.keys():
    #    context.user_name = os.environ["USER"]
    #    logger.debug("Set user name from $USER :" + context.user_name)

    # START PROCESSING
    # ------------------------------

    # initialize console context
    context.register_utilities()

    # start processor
    result = context.process(sys.argv)
    if result:
        sys.exit(int(result))
