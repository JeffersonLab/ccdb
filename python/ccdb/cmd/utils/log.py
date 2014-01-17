import os
import logging

import ccdb
from ccdb import TextFileDOM
from ccdb import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase
from ccdb.model import LogRecord
from ccdb import BraceMessage as LogFmt

log = logging.getLogger("ccdb.cmd.utils.log")


#ccdbcmd module interface
def create_util_instance():
    """
    This function is a module interface

    :return: new ShowLog util
    :rtype: ShowLog
    """
    log.debug("      registering ShowLog")
    return ShowLog()


#*********************************************************************
#   Class ShowLog - Add data constants                               *
#                                                                    *
#*********************************************************************
class ShowLog(ConsoleUtilBase):
    """ Show log record"""
    
    # ccdb utility class descr part 
    #------------------------------
    command = "log"
    name = "ShowLog"
    short_descr = "Shows log records"
    uses_db = True

    def __init(self):
        pass

    #----------------------------------------
    #   process
    #----------------------------------------
    def process(self, args):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}ShowLog is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args)+"'"))

        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        offset = 0
        limit = 10

        if len(args) == 1:
            limit = int(args[0])
        if len(args) == 2:
            offset = int(args[1])

        log_records = provider.get_log_records(limit=limit, offset=offset)

        if not log_records:
            print ("No log records found")
            return 0

        print self.theme.Directories + "(action)        (author)         (date)                 (description)"

        for log_record in log_records:
            assert isinstance(log_record, LogRecord)
            print " %-13s "%log_record.action +\
                  " %-16s"%log_record.author.name + \
                  " %-18s"%log_record.created.strftime("%Y-%m-%d %H-%M-%S   ") + " " +\
                  log_record.description





#----------------------------------------
#   print_help 
#----------------------------------------
    def print_help(self):
        """Prints help of the command"""
          
        print """Shows log records
    log <records to show>  <records to skip>

Example:
    > log
    > log 50
    """
