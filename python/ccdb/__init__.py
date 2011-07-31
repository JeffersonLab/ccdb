#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#       untitled.py
#
#       Copyright 2010 root <root@romanov-pcl1.jlab.org>
#
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

import glob
import imp
import os
import sys
import logging

from cmd import set_verbose, get_verbose, VerboseModes, Theme
from cmd import ConsoleContext

import cmd.colorama
import ccdb_pyllapi

from ProviderBase import ProviderBase
from MySQLProvider import MySQLProvider
from ccdb_pyllapi import Variation, Directory, RunRange, Assignment, ConstantsTypeColumn, ConstantsTypeTable, StringStringMap, StringVectorVector, StringVector
from TextFileDOM import TextFileDOM, read_ccdb_text_file, read_namevalue_text_file

#the default ccdb logger
logger = logging.getLogger("ccdb")

__all__ = ["MySQLProvider", "ProviderBase", "ccdb_pyllapi", "TextFileDOM"]

INFINITE_RUN = 2147483647

def init_ccdb_console():
    # create logger
    logger = logging.getLogger("ccdb")
    
    #create and set console handler
    ch = logging.StreamHandler()
    ch.stream = sys.stdout
    logger.addHandler(ch)
        
    # CHECK SOME COMMAND LINE KEYS
    #------------------------------
    if "--s" in sys.argv or "--silent" in sys.argv:
        logger.setLevel(logging.CRITICAL)
    else:
        logger.setLevel(logging.INFO)

    if "--no-color" in sys.argv:
        #no colors for output
        cmd.colorama.init(False, False, False, False)
    else:
        #colors are ON
        cmd.colorama.init(autoreset=True)

    if "--debug" in sys.argv or "-dv" in sys.argv:
        set_verbose(VerboseModes.Debug)   
        logger.setLevel(logging.DEBUG)
        logger.debug("debugging verbose mode is " + Theme.Ok + " ON " + Theme.Reset + " value is " + repr(get_verbose()))
        
    #lets go
    #logger.info("Initialising ccdb package...")

    #create console context
    context = ConsoleContext();

    #PROCESS ENVIRONMENT VARIABLES
    #------------------------------

    #connection string
    if "CCDB_CONNECTION" in os.environ.keys():
        context.connection_string =  os.environ["CCDB_CONNECTION"]
        logger.debug("Set connection string from $CCDB_CONNECTION :" + context.connection_string)

    if "CCDB_USER" in os.environ.keys():
        context.user_name =  os.environ["CCDB_USER"]        
        logger.debug("Set user name from $CCDB_USER :" + context.user_name)


    # START PROCESSING
    #------------------------------

    #initialize console context
    modules = context.register_utilities();

    #start processor
    context.process(sys.argv)    