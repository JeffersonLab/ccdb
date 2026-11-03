import os
import logging
from sqlalchemy import desc

from ccdb import AlchemyProvider
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb.model import LogRecord
from ccdb import BraceMessage as LogFmt

log = logging.getLogger("ccdb.cmd.commands.log")


# ********************************************************************
#      Class ShowLog - Add data constants                            *
#*********************************************************************
class ShowLog(CliCommandBase):
    """ Show log record"""
    
    # ccdb utility class descr part 
    #------------------------------
    command = "log"
    name = "ShowLog"
    short_descr = "Shows log records"
    uses_db = True

    #----------------------------------------
    #   process
    #----------------------------------------
    def execute(self, args):
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
        return True

    DEFAULT_LIMIT = 20

    def process_arguments(self, args):
        """`log [N] [SKIP]` shows the newest N records (20 by default) after skipping SKIP; a positional that is not
        a number is a table path or pattern, as `-t` (so `log /dir/table` keeps working)"""
        # utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("positionals", nargs="*", default=[])
        parser.add_argument("-t", "--table", default="")
        parser.add_argument("-v", "--variation", default="")
        parser.add_argument("-u", "--user", default="")
        parser.add_argument("-d", "--date", default="") # TODO: Implement filter by date
        result = parser.parse_args(args)
        numbers = [int(value) for value in result.positionals if value.lstrip("-").isdigit()]
        names = [value for value in result.positionals if not value.lstrip("-").isdigit()]
        if len(numbers) > 2 or len(names) > 1:
            raise ValueError("log takes at most two numbers (records to show, records to skip) and one table name")
        result.limit = numbers[0] if numbers else self.DEFAULT_LIMIT
        result.offset = numbers[1] if len(numbers) > 1 else 0
        if result.limit < 0 or result.offset < 0:
            raise ValueError("log: the number of records to show and to skip cannot be negative")
        result.obj_name = names[0] if names else ""
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

        # newest first, a page of them: `log` alone never streams the whole table (F33)
        query = query.order_by(desc(LogRecord.id))
        if result.offset:
            query = query.offset(result.offset)
        if result.limit:
            query = query.limit(result.limit)
        return query.all()


#----------------------------------------
#   print logs
#----------------------------------------
    def print_logs(self, log_records):

        print(self.theme.Directories + "(action)        (author)         (date)                 (description)" + self.theme.Reset)

        for log_record in log_records:
            print(" %-13s "%log_record.action +\
                " %-16s"%log_record.author.name + \
                " %-18s"%log_record.created.strftime("%Y-%m-%d %H-%M-%S   ") + " " +\
                 log_record.description)


#----------------------------------------
#   print_help 
#----------------------------------------
    def print_help(self):
        """Prints help of the command"""
          
        print("""Shows log records, the newest first
    log [<records to show>] [<records to skip>] [<table>]

    records to show   - how many records to print (20 by default; 0 prints all)
    records to skip   - how many of the newest records to skip (paging)
    table             - a table path or a pattern with * and ?; only records that name it
    -t, --table       - the same as the table argument
    -v, --variation   - only records that name the variation
    -u, --user        - only records by this user

Example:
    > log
    > log 50
    > log 50 100
    > log /test/test_vars/test_table
    > log -u test_user 10
    """)
