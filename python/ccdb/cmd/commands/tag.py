import logging
import os
from datetime import timezone

from ccdb import AlchemyProvider
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb.path_utils import parse_time
from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.brace_log_message import BraceMessage as LogFmt

log = logging.getLogger("ccdb.cmd.commands.tag")


def print_tag(theme, tag, variation):
    """Prints one tag: name, variation, time (UTC and local), author, comment"""
    utc = tag.snapshot_time.replace(tzinfo=timezone.utc)
    print(" Tag        :  " + theme.Success + tag.name + theme.Reset)
    print(" Variation  :  " + variation.name)
    print(" Time (UTC) :  " + utc.strftime("%Y-%m-%d %H:%M:%S"))
    print(" Time (loc) :  " + utc.astimezone().strftime("%Y-%m-%d %H:%M:%S"))
    print(" DB Id      :  " + repr(int(tag.id)))
    print(" Comment    :  " + (tag.comment or ""))


# ********************************************************************
#   Class Tag - creates, lists, shows and removes tags               *
# ********************************************************************
class TagCommand(CliCommandBase):
    """ Creates, lists, shows and removes tags """

    # ccdb utility class descr part
    # ------------------------------
    command = "tag"
    name = "Tag"
    short_descr = "Creates, lists, shows or removes snapshot tags"
    uses_db = True

    def execute(self, args):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Tag is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args) + "'"))

        assert self.context is not None
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        # remove
        if len(args) >= 1 and args[0] == "rm":
            if len(args) != 2:
                raise ValueError("Usage: tag rm NAME")
            provider.delete_tag(args[1])
            log.info(LogFmt("Tag '{0}' is removed", args[1]))
            return True

        parsed = self._process_arguments(args)

        # list
        if not parsed.name:
            if parsed.variation or parsed.time or parsed.comment:
                raise ValueError("A tag name is required to create a tag. See 'help tag'")
            self.print_tags(provider)
            return True

        # show
        if not (parsed.variation or parsed.time or parsed.comment):
            tag = provider.get_tag(parsed.name)
            print_tag(self.theme, tag, provider.get_tag_variation(tag))
            return tag

        # create
        if not parsed.comment:
            raise ValueError("A comment is required to create a tag: -c COMMENT")

        snapshot_time = None
        if parsed.time:
            try:
                local_time = parse_time(parsed.time)
            except ValueError as ex:
                raise ValueError("Cannot parse -t/--time value '{}' ({}). "
                                 "-t expects a date like 2012-08 or 2012-08-30-14-00-00"
                                 .format(parsed.time, ex)) from ex
            # a user gives local time; the tag stores the UTC instant
            snapshot_time = local_time.astimezone(timezone.utc).replace(tzinfo=None)

        tag = provider.create_tag(parsed.name, parsed.variation or "default", snapshot_time, parsed.comment)
        log.info(LogFmt("Tag '{0}' is created", tag.name))
        return tag

    @staticmethod
    def _process_arguments(args):
        parser = UtilityArgumentParser()
        parser.add_argument("name", nargs='?', default="")
        parser.add_argument("-v", "--variation", default="")
        parser.add_argument("-t", "--time", default="")
        parser.add_argument("-c", "--comment", default="")
        return parser.parse_args(args)

    def print_tags(self, provider):
        tags = provider.get_tags()
        if not tags:
            print("No tags")
            return
        variation_names = {}
        print(self.theme.Directories + "(name)                (variation)      (time UTC)            (comment)"
              + self.theme.Reset)
        for tag in tags:
            if tag.variation_id not in variation_names:
                try:
                    variation_names[tag.variation_id] = provider.get_tag_variation(tag).name
                except ObjectIsNotFoundInDbError:
                    variation_names[tag.variation_id] = "<deleted>"
            print(" %-20s " % tag.name +
                  " %-15s " % variation_names[tag.variation_id] +
                  " %-20s " % tag.snapshot_time.strftime("%Y-%m-%d %H:%M:%S") +
                  " " + (tag.comment or "").replace(os.linesep, " "))

    def print_help(self):
        """Prints help of the command"""
        print("""Creates, lists, shows or removes snapshot tags

A tag names the state of a variation at one moment. A request with a tag gets the data
of the tag variation that existed at the tag time:
   cat /test/test_vars/test_table:1000@mytag

    tag                                       - lists tags
    tag NAME                                  - shows the tag
    tag NAME [-v VARIATION] [-t TIME] -c TEXT - creates the tag
    tag rm NAME                               - removes the tag

 Flags:
    -v or --variation - the variation of the tag, 'default' if not given
    -t or --time      - the moment of the tag, local time, now if not given. A future time is refused
    -c or --comment   - the comment of the tag, required to create one

A request with a tag can have neither a variation nor a time: /test/table::mc@mytag is an error.

Examples:
   >> tag run2025 -c "Calibrations of the 2025 run"
   >> tag mc_spring -v mc -t 2025-04-01 -c "MC as of April"
   >> cat /test/test_vars/test_table@run2025
   >> vers /test/test_vars/test_table@run2025
   >> tag rm run2025
""")
