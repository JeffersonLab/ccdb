
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

from .provider import AlchemyProvider
from .model import Variation, RunRange, Assignment, ConstantSet, Directory, TypeTable, TypeTableColumn
from .table_file import TextFileDOM, read_ccdb_text_file, read_namevalue_text_file
from .cmd.themes import NoColorTheme, ColoredTheme
from .brace_log_message import BraceMessage
import cmd.themes

#the default ccdb logger
logger = logging.getLogger("ccdb")

INFINITE_RUN = 2147483647



def init_ccdb_console():
    from .cmd.themes import Theme
    from .cmd import ConsoleContext
    import cmd.colorama

    # create logger
    logger = logging.getLogger("ccdb")

    #create and set console handler
    ch = logging.StreamHandler()
    ch.stream = sys.stdout
    #formatter = logging.Formatter('%(message)s', style='{')
    #ch.setFormatter(formatter)
    logger.addHandler(ch)

    #create console context
    context = ConsoleContext()

    # CHECK SOME COMMAND LINE KEYS
    #------------------------------
    if "-s" in sys.argv or "--silent" in sys.argv:
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.INFO)

    cmd.colorama.init(autoreset=True)

    if "--no-color" in sys.argv:
        #no colors for output
        context.theme = NoColorTheme
    else:
        #colors are ON
        context.theme = ColoredTheme

    if "--debug" in sys.argv:
        logger.setLevel(logging.DEBUG)
        logger.debug("debugging verbose mode is " + context.theme.Ok + " ON " + context.theme.Reset)

    if "--raise" in sys.argv:
        logger.debug("--raise flag found. The process will raise commands exceptions instead of humble notifications and non 0 result")
        context.silent_exceptions = False
        

    #CONNECTION STRING
    #------------------------------

    #this is default connection string (for a fallback)
    context.connection_string = "mysql://ccdb_user@localhost/ccdb"

    #connection string
    if "CCDB_CONNECTION" in os.environ.keys():
        context.connection_string =  os.environ["CCDB_CONNECTION"]
        logger.debug("Set connection string from $CCDB_CONNECTION :" + context.connection_string)
    else:
        #fallback to jana calib url
        if "JANA_CALIB_URL" in os.environ.keys():
            jana_url = os.environ["JANA_CALIB_URL"]
            logger.debug("$CCDB_CONNECTION was not found. Found JANA_CALIB_URL ('"+jana_url+"'). Try use it")

            if jana_url.startswith("mysql://") or jana_url.startswith("sqlite://"):
                context.connection_string = jana_url
            else:
                logger.debug("JANA_CALIB_URL does not starts with mysql:// or sqlite://. Skipped")


    #connection string in in command line arguments ( by -c or --connection) is processed by context.process(sys.argv)

    if "CCDB_USER" in os.environ.keys():
        context.user_name =  os.environ["CCDB_USER"]        
        logger.debug("Set user name from $CCDB_USER :" + context.user_name)


    # START PROCESSING
    #------------------------------

    #initialize console context
    context.register_utilities()

    #start processor
    result = context.process(sys.argv)
    if result: sys.exit(int(result))