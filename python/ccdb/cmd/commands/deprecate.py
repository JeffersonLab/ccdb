import logging
import os

from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.provider import AlchemyProvider
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb import BraceMessage as LogFmt

log = logging.getLogger("ccdb.cmd.commands.deprecate")


# ********************************************************************
#   Class Deprecate - Marks or unmarks an object as deprecated      *
# ********************************************************************
class Deprecate(CliCommandBase):
    """ Marks a table, a directory or a variation as deprecated """

    # ccdb utility class descr part
    #------------------------------
    command = "deprecate"
    name = "Deprecate"
    short_descr = "Marks a table, a directory or a variation as deprecated"
    uses_db = True

    def execute(self, args):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Deprecate is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args) + "'"))

        assert self.context is not None
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        result = self._process_arguments(args)

        if not result.undo and (result.comment is None or not result.comment.strip()):
            raise ValueError("A comment is required: deprecate NAME -c \"why and what to use instead\"")

        obj, kind = self._find_object(provider, result)

        if result.undo:
            provider.undeprecate(obj)
            log.info(LogFmt("{0} '{1}' {2}is no longer deprecated{3}",
                            kind, self._display_name(obj), self.theme.Success, self.theme.Reset))
        else:
            provider.deprecate(obj, result.comment)
            log.info(LogFmt("{0} '{1}' {2}deprecated{3}",
                            kind, self._display_name(obj), self.theme.Success, self.theme.Reset))

        # The CLI treats a None result as failure (exit code 1), so report success
        return True

    @staticmethod
    def _process_arguments(args):
        # utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("obj_name")
        parser.add_argument("-t", "--table", action="store_true")
        parser.add_argument("-d", "--directory", action="store_true")
        parser.add_argument("-v", "--variation", action="store_true")
        parser.add_argument("-c", "--comment", default=None)
        parser.add_argument("--undo", action="store_true")

        result = parser.parse_args(args)
        if result.table + result.directory + result.variation > 1:
            raise ValueError("Use only one of -t, -d and -v")
        return result

    def _find_object(self, provider, result):
        """Finds the object to (un)deprecate. Without a flag the name is tried as a table, then as a directory"""
        if result.variation:
            return provider.get_variation(result.obj_name), "Variation"

        path = self.context.prepare_path(result.obj_name)

        if result.directory:
            return provider.get_directory(path), "Directory"

        if result.table:
            return provider.get_type_table(path), "Table"

        try:
            return provider.get_type_table(path), "Table"
        except ObjectIsNotFoundInDbError:
            log.debug(LogFmt(" |- no table '{0}', trying it as a directory", path))

        try:
            return provider.get_directory(path), "Directory"
        except ObjectIsNotFoundInDbError:
            message = "No table or directory found by path '{0}'. Use -v for a variation".format(path)
            raise ObjectIsNotFoundInDbError(None, message)

    @staticmethod
    def _display_name(obj):
        return getattr(obj, "path", None) or obj.name

    def print_help(self):
        """Prints help of the command"""

        print("""Marks a table, a directory or a variation as deprecated

A deprecated object works as before: requests, cat, vers, dump and info are unchanged.
ls hides deprecated entries; ls -a shows them marked, ls -l adds the comment and the date.

    deprecate <name> -c <comment>         - deprecates a table, or a directory if there is no such table
    deprecate <name> -t -c <comment>      - deprecates a table
    deprecate <name> -d -c <comment>      - deprecates a directory
    deprecate <name> -v -c <comment>      - deprecates a variation
    deprecate --undo <name> [-t|-d|-v]    - clears the deprecation

keys:
    -t or --table        - the name is a table
    -d or --directory    - the name is a directory
    -v or --variation    - the name is a variation
    -c or --comment      - why the object is deprecated and what to use instead (required)
    --undo               - clears the deprecation

examples:
    deprecate /test/old_table -c "Use /test/new_table"
    deprecate --undo /test/old_table
""")
