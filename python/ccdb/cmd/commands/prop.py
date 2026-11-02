import logging
import os

from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb import AlchemyProvider
from ccdb import BraceMessage as LogFmt
from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.model import Property


log = logging.getLogger("ccdb.cmd.commands.prop")


# ********************************************************************
#   Class Prop - sets, gets and lists properties                     *
# ********************************************************************
class Prop(CliCommandBase):
    """ Sets, gets and lists properties of the instance and of objects """

    # ccdb utility class descr part
    #------------------------------
    command = "prop"
    name = "Prop"
    short_descr = "Sets, gets and lists properties of the instance, tables, directories and variations"
    uses_db = True

    actions = ("set", "get", "ls", "rm")

    #----------------------------------------
    #   process
    #----------------------------------------
    def execute(self, args):
        if log.isEnabledFor(logging.DEBUG):
            log.debug(LogFmt("{0}Prop is in charge{0}\\".format(os.linesep)))
            log.debug(LogFmt(" |- arguments : '" + "' '".join(args) + "'"))

        assert self.context
        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)

        parsed = self._process_arguments(args)
        words = list(parsed.words)

        # the instance has no name, so with --instance every word after the action is the key and the value
        if parsed.instance:
            owner_type, owner_id, owner_title = "instance", 0, "the instance"
        else:
            if not words:
                raise ValueError("No object name is given. Use --instance or 'prop {0} NAME ...'. "
                                 "See 'help prop'".format(parsed.action))
            owner_type, owner_id, owner_title = self._resolve_owner(provider, words.pop(0), parsed)

        if parsed.action == "ls":
            for prop in provider.get_properties(owner_type, owner_id):
                print(prop.name + " = " + prop.value)
            return True

        if not words:
            raise ValueError("No property name is given. See 'help prop'")
        key = words.pop(0)

        if parsed.action == "get":
            prop = provider.get_property(owner_type, owner_id, key)
            if prop is None:
                raise ObjectIsNotFoundInDbError(Property, "{0} has no property '{1}'".format(owner_title, key))
            print(prop.value)
            return prop.value

        if parsed.action == "rm":
            provider.delete_property(owner_type, owner_id, key)
            log.info(LogFmt("Deleted property '{0}' of {1}", key, owner_title))
            return True

        # set: the words after the key are the value, so it needs no quotes
        if not words:
            raise ValueError("No value is given for property '{0}'. See 'help prop'".format(key))
        value = " ".join(words)
        provider.set_property(owner_type, owner_id, key, value)
        log.info(LogFmt("Property '{0}' of {1} is set", key, owner_title))
        return True

    def _resolve_owner(self, provider, obj_name, parsed):
        """The owner type, its id and a title for messages, for the object the name refers to"""
        if parsed.variation:
            variation = provider.get_variation(obj_name)
            return "variation", variation.id, "variation '{0}'".format(variation.name)
        path = self.context.prepare_path(obj_name)
        if parsed.directory:
            directory = provider.get_directory(path)
            return "directory", directory.id, "directory '{0}'".format(directory.path)
        table = provider.get_type_table(path)
        return "table", table.id, "table '{0}'".format(table.path)

    #----------------------------------------
    #   process_arguments
    #----------------------------------------
    def _process_arguments(self, args):
        #utility argument parser is argparse which raises errors instead of exiting app
        parser = UtilityArgumentParser()
        parser.add_argument("action", choices=self.actions)
        parser.add_argument("words", nargs="*")
        parser.add_argument("--instance", action="store_true")
        owner = parser.add_mutually_exclusive_group()
        owner.add_argument("-t", "--table", action="store_true")
        owner.add_argument("-d", "--directory", action="store_true")
        owner.add_argument("-v", "--variation", action="store_true")

        # intermixed: the flags may come after the words, as in 'prop ls default -v'
        result = parser.parse_intermixed_args(args)
        if result.instance and (result.table or result.directory or result.variation):
            raise ValueError("--instance can not be used with -t, -d or -v")

        log.debug(LogFmt(" |- parsed as (action: '{0}', words: '{1}', instance: '{2}')",
                         result.action, result.words, result.instance))
        return result

    #----------------------------------------
    #   print_help
    #----------------------------------------
    def print_help(self):
        """Prints help of the command"""

        print("""Sets, gets and lists properties: named values of the instance, tables, directories and variations
    prop set --instance <key> <value>     - sets a property of the instance (the whole database)
    prop get --instance <key>             - prints the value of an instance property
    prop ls  --instance                   - lists the instance properties
    prop rm  --instance <key>             - deletes an instance property

    prop set <name> <key> <value>         - the same for a table; <name> is a table path
    prop get <name> <key>
    prop ls  <name>
    prop rm  <name> <key>

    flags for <name>:
    -t, --table      - <name> is a table path (the default)
    -d, --directory  - <name> is a directory path
    -v, --variation  - <name> is a variation name

Setting an existing key replaces its value. Each change is written to the log.
Known instance keys: experiment, description, license, citation, contact, url
Known object keys:   description, contact, keywords, source_url, doc_url, license, citation
Any other key is allowed too.

Examples:
   >> prop set --instance experiment GlueX
   >> prop set /test/test_vars/test_table doc_url https://example.org/test_table
   >> prop set -d /test contact "Jane Doe"
   >> prop ls -v default
   >> info /test/test_vars/test_table      #shows the table properties too
    """)
