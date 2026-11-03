"""`ccdb provenance FILE.json [--tag]`: checks a record of the constants a job resolved against the database.

The record is what the JANA2 service writes with ccdb:provenance=PATH, or a Python program's
AlchemyProvider.resolved_assignments dumped as JSON (docs/apis/jana.md, "What a job used"). For every entry the
command checks that the assignment exists, belongs to the table named, and that its stored SHA-256 equals the one
the job received; it also shows what the same request resolves to today. With --tag it lists the tags that give
every entry's assignment, so a job can be matched to the processing pass it belongs to.

Exit code 1 when an entry's assignment is missing or its hash differs; the command only reads.
"""
import datetime
import json
import logging

from sqlalchemy.exc import NoResultFound

from ccdb import AlchemyProvider
from ccdb.cmd import CliCommandBase, UtilityArgumentParser
from ccdb.errors import ObjectIsNotFoundInDbError

log = logging.getLogger("ccdb.cmd.commands.provenance")


def read_record(path):
    """The entries of a record file: the JANA2 form {"resolved": [...]} or a bare list of entries"""
    with open(path, encoding="utf-8") as file:
        content = json.load(file)
    entries = content.get("resolved", []) if isinstance(content, dict) else content
    if not isinstance(entries, list) or not all(isinstance(each, dict) for each in entries):
        raise ValueError("{0}: expected a JSON list of entries or an object with 'resolved'".format(path))
    return entries


class Provenance(CliCommandBase):
    """Checks a record of resolved constants against the database"""

    command = "provenance"
    name = "Provenance"
    short_descr = "check the record of the constants a job used (ccdb:provenance) against the database"
    uses_db = True

    def execute(self, args):
        parser = UtilityArgumentParser(prog="ccdb provenance")
        parser.add_argument("file", help="the JSON record a job wrote (ccdb:provenance) or resolved_assignments")
        parser.add_argument("--tag", action="store_true", help="list the tags that give every entry's assignment")
        options = parser.parse_args(args)

        provider = self.context.provider
        assert isinstance(provider, AlchemyProvider)
        entries = read_record(options.file)

        failures = 0
        print("{0:<8} {1:>10} {2:<14} {3:<16} {4}".format("(check)", "(id)", "(sha256)", "(today)", "(request)"))
        for entry in entries:
            status = self.check_entry(provider, entry)
            failures += status != "ok"
            today = self.resolve_today(provider, entry)
            if today is None:
                today_text = "no data"
            elif today == entry.get("assignment_id"):
                today_text = "same"
            else:
                today_text = "now {0}".format(today)
            print("{0:<8} {1:>10} {2:<14} {3:<16} {4}".format(status, entry.get("assignment_id"),
                                                             str(entry.get("sha256", ""))[:12], today_text,
                                                             entry.get("request", entry.get("path", ""))))
        print("{0} of {1} entries match the database".format(len(entries) - failures, len(entries)))

        if options.tag:
            matching = [tag.name for tag in provider.get_tags()
                        if entries and all(self.resolve_with_tag(provider, entry, tag) == entry.get("assignment_id")
                                           for entry in entries)]
            print("tags that give every entry: " + (", ".join(matching) if matching else "none"))

        return failures == 0

    @staticmethod
    def check_entry(provider, entry):
        """ok, MISSING (no such assignment), TABLE (another table's assignment) or HASH (other data)"""
        try:
            assignment = provider.get_assignment_by_id(int(entry["assignment_id"]))
        except (KeyError, ValueError, TypeError, ObjectIsNotFoundInDbError, NoResultFound):
            return "MISSING"
        if assignment is None:
            return "MISSING"
        if entry.get("path") and assignment.constant_set.type_table.path != entry["path"]:
            return "TABLE"
        if assignment.constant_set.sha256 != entry.get("sha256"):
            return "HASH"
        return "ok"

    @staticmethod
    def resolve_today(provider, entry):
        """The id the entry's request resolves to now, None when nothing does"""
        try:
            if entry.get("tag"):
                assignment = provider.get_assignment(entry["path"], int(entry["run"]), "", tag=entry["tag"])
            else:
                time = None
                if entry.get("time"):
                    time = datetime.datetime.strptime(entry["time"], "%Y-%m-%dT%H:%M:%S.%fZ") \
                        .replace(tzinfo=datetime.timezone.utc)
                assignment = provider.get_assignment(entry["path"], int(entry["run"]),
                                                     entry.get("variation") or "default", time)
            return assignment.id
        except (KeyError, ValueError, ObjectIsNotFoundInDbError, NoResultFound):
            return None

    @staticmethod
    def resolve_with_tag(provider, entry, tag):
        try:
            return provider.get_assignment(entry["path"], int(entry["run"]), "", tag=tag).id
        except (KeyError, ValueError, ObjectIsNotFoundInDbError, NoResultFound):
            return None

    def print_help(self):
        print("""Checks a record of the constants a job resolved against the database

    ccdb provenance FILE.json          # every entry: assignment present, same table, same SHA-256
    ccdb provenance FILE.json --tag    # also the tags that give every entry's assignment

FILE.json is what the JANA2 service writes with ccdb:provenance=PATH, or AlchemyProvider.resolved_assignments
saved as JSON. Columns: the check (ok, MISSING, TABLE, HASH), the assignment id, the start of its SHA-256, what the
same request resolves to today (same, now ID, no data) and the request. Exit code 1 when an entry fails.
""")
