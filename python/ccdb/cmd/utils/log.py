import os
import logging
from sqlalchemy import desc

import ccdb
from ccdb import TextFileDOM
from ccdb import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase, UtilityArgumentParser
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

        result = self.process_arguments(args)
        log_records = self.filter(result)

        if len(log_records) == 0:
            print("No entries matching the filter criteria.")
        else:
            self.print_logs(log_records)

    def process_arguments(self, args):
        # utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("obj_name", nargs="?", default="")
        parser.add_argument("-t", "--table", default="")
        parser.add_argument("-v", "--variation", default="")
        parser.add_argument("-u", "--user", default="")
        parser.add_argument("-d", "--date", default="") # TODO: Implement filter by date
        result = parser.parse_args(args)
        return result

# ----------------------------------------
#   filtering
# ----------------------------------------
    def filter(self, result):

        query = self.context.provider.session.query(LogRecord)

        if result.user: # filter by user
            user_id = self.context.provider.get_user(result.user).id
            query = query.filter(LogRecord.author_id.like("{0}".format(user_id)))

        if result.table or result.obj_name: # filter by table

            user_input = result.obj_name if result.obj_name else result.table

            user_input = user_input.replace("_", "\\_").replace("*", "%").replace("?", "_")
            full_table_path = self.context.prepare_path(user_input)
            query = query.filter(LogRecord.description.like("%'{0}%:%:%:%".format(full_table_path)))

        if result.variation: # filter by variation
            query = query.filter(LogRecord.description.like("%:%:{0}:%".format(result.variation)))

        query.order_by(desc(LogRecord.id))

        return query.all()


#----------------------------------------
#   print logs
#----------------------------------------
    def print_logs(self, log_records):

        print self.theme.Directories + "(action)        (author)         (date)                 (description)"

        for log_record in log_records:
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
