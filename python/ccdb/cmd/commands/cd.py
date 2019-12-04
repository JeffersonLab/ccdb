import logging
from ccdb.cmd import CliCommandBase

log = logging.getLogger("ccdb.cmd.commands.cd")


# ********************************************************************
#   Class ChangeDir - Change current directory                       *
# ********************************************************************
class ChangeDir(CliCommandBase):
    """ Change current directory """
    
    # ccdb utility class descr part
    command = "cd"
    name = "ChangeDir"
    short_descr = "Change current directory"
    uses_db = True

    def print_help(self):
        print(""" Change current directory """)

    def execute(self, args):
        log.debug("  ChangeDir is gained a control over the process.")
        log.debug("    ".join(args))
        
        raw_entry = args[0] if len(args) else "/"

        # Normalize '/' and joins with the current path if not absolute
        raw_entry = self.context.prepare_path(raw_entry)

        # try to find the directory
        directory = self.context.provider.get_directory(raw_entry)
        self.context.current_path = raw_entry
        return directory
