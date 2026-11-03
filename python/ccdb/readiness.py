"""The readiness profile of a CCDB instance: counts that show how well programs can find, understand and trust its
constants (docs/concepts/ai-readiness.md).

    from ccdb.readiness import profile
    numbers = profile(provider)                  # a dict of plain values, ready for json.dumps

Every number is one SQL count over the whole database; nothing is sampled. Two profiles of the same data made on the
same UTC day are equal apart from `generated`, so profiles of two snapshots or two instances compare line by line.
The staleness cutoff is the start of the UTC day of `generated` minus `stale_years` years; it is echoed in `config`.

The profile describes; it does not judge. Which numbers matter depends on what the instance is for.
"""
import datetime

from sqlalchemy import func, select, exists, and_

from ccdb.model import (Assignment, CcdbSchemaVersion, ConstantSet, Directory, Property, RunRange, Tag, TypeTable, TypeTableColumn, User,
                        Variation, INFINITE_RUN)
from ccdb.version import version as ccdb_version

DEFAULT_STALE_YEARS = 5

# Properties whose presence the profile reports; docs/cli.md lists what each one means
INSTANCE_PROPERTIES = ("license", "citation", "contact", "experiment", "url")
TABLE_PROPERTIES = ("contact", "source_url", "doc_url")


def stale_cutoff(generated, stale_years):
    """The start of the UTC day of `generated`, `stale_years` years back (29 February becomes 28 February)"""
    day = generated.date()
    try:
        start = day.replace(year=day.year - stale_years)
    except ValueError:
        start = day.replace(year=day.year - stale_years, day=28)
    return datetime.datetime(start.year, start.month, start.day)


def utc_text(moment):
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def profile(provider, stale_years=DEFAULT_STALE_YEARS, generated=None):
    """The readiness profile of the database `provider` is connected to, as a dict of groups of counts.

    generated is the naive UTC moment the profile describes (now, by default); tests pass a fixed one."""
    if stale_years < 0:
        raise ValueError("stale_years must be 0 or more, got {0}".format(stale_years))
    generated = generated or datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None, microsecond=0)
    cutoff = stale_cutoff(generated, stale_years)
    session = provider.session

    def count(statement):
        return int(session.execute(statement).scalar() or 0)

    def non_empty(column):
        return and_(column.isnot(None), func.trim(column) != "")

    def owners_with_property(owner_type, name):
        return count(select(func.count(func.distinct(Property.owner_id)))
                     .where(Property.owner_type == owner_type, Property.name == name, non_empty(Property.value)))

    # the newest assignment of each table that has any; tables without assignments are counted as empty instead
    newest_per_table = (select(ConstantSet.type_table_id, func.max(Assignment.created).label("newest"))
                        .join(Assignment, Assignment.constant_set_id == ConstantSet.id)
                        .group_by(ConstantSet.type_table_id).subquery())
    tables_with_data = count(select(func.count()).select_from(newest_per_table))
    shared_sets = (select(Assignment.constant_set_id).group_by(Assignment.constant_set_id)
                   .having(func.count(Assignment.id) > 1).subquery())
    unbounded = Assignment.run_range_id == RunRange.id

    tables = count(select(func.count(TypeTable.id)))
    instance_names = {name for (name,) in session.execute(
        select(Property.name).where(Property.owner_type == "instance", non_empty(Property.value)))}

    return {
        "config": {
            "stale_years": stale_years,
            "stale_before": utc_text(cutoff),
            "generated": utc_text(generated),
            "ccdb_version": ccdb_version,
            "schema_version": count(select(func.max(CcdbSchemaVersion.version))),
        },
        "metadata": {
            "columns": count(select(func.count(TypeTableColumn.id))),
            "columns_with_units": count(select(func.count(TypeTableColumn.id)).where(non_empty(TypeTableColumn.units))),
            "tables": tables,
            "tables_with_description": count(select(func.count(TypeTable.id)).where(non_empty(TypeTable.comment))),
            "versions": count(select(func.count(Assignment.id))),
            "versions_with_comment": count(select(func.count(Assignment.id)).where(non_empty(Assignment._comment))),
            **{"tables_with_" + name: owners_with_property("table", name) for name in TABLE_PROPERTIES},
        },
        "units": {
            "columns_with_ucum_units": None,
        },
        "history": {
            # a range from run N > 0 to infinity: later runs silently get these constants
            "open_ended_run_ranges": count(select(func.count(Assignment.id)).join(RunRange, unbounded)
                                           .where(RunRange.max == INFINITE_RUN, RunRange.min > 0)),
            # a range from run 0 to infinity: one value for every run
            "versions_for_all_runs": count(select(func.count(Assignment.id)).join(RunRange, unbounded)
                                           .where(RunRange.max == INFINITE_RUN, RunRange.min <= 0)),
            "versions_by_anonymous": count(select(func.count(Assignment.id)).join(User, Assignment.author_id == User.id)
                                           .where(User.name == "anonymous")),
            "stale_tables": count(select(func.count()).select_from(newest_per_table)
                                  .where(newest_per_table.c.newest < cutoff)),
            "empty_tables": tables - tables_with_data,
            "deprecated_tables": count(select(func.count(TypeTable.id)).where(TypeTable.is_deprecated.is_(True))),
            "deprecated_variations": count(select(func.count(Variation.id)).where(Variation.is_deprecated.is_(True))),
            "deprecated_directories": count(select(func.count(Directory.id)).where(Directory.is_deprecated.is_(True))),
            "tags": count(select(func.count(Tag.id))),
        },
        "data": {
            "constant_sets": count(select(func.count(ConstantSet.id))),
            "shared_sets": count(select(func.count()).select_from(shared_sets)),
            "unused_sets": count(select(func.count(ConstantSet.id)).where(
                ~exists().where(Assignment.constant_set_id == ConstantSet.id))),
            "bytes": count(select(func.sum(ConstantSet.size))),
        },
        "instance": {name: name in instance_names for name in INSTANCE_PROPERTIES},
    }


# The text form: (group, field, label, the field it is a share of)
TEXT_ROWS = [
    ("metadata", "columns_with_units", "columns with units", "columns"),
    ("units", "columns_with_ucum_units", "columns with UCUM units", "columns"),
    ("metadata", "tables_with_description", "tables with a description", "tables"),
    ("metadata", "tables_with_contact", "tables with a contact", "tables"),
    ("metadata", "tables_with_source_url", "tables with a source_url", "tables"),
    ("metadata", "tables_with_doc_url", "tables with a doc_url", "tables"),
    ("metadata", "versions_with_comment", "versions with a comment", "versions"),
    ("history", "open_ended_run_ranges", "versions open-ended (run N to infinity)", "versions"),
    ("history", "versions_for_all_runs", "versions for all runs (0 to infinity)", "versions"),
    ("history", "versions_by_anonymous", "versions by anonymous", "versions"),
    ("history", "stale_tables", "stale tables", "tables"),
    ("history", "empty_tables", "empty tables", "tables"),
    ("history", "deprecated_tables", "deprecated tables", "tables"),
    ("history", "deprecated_variations", "deprecated variations", None),
    ("history", "deprecated_directories", "deprecated directories", None),
    ("history", "tags", "tags", None),
    ("data", "constant_sets", "constant sets", None),
    ("data", "shared_sets", "shared sets (more than one version)", "constant_sets"),
    ("data", "unused_sets", "unused sets (no version)", "constant_sets"),
    ("data", "bytes", "bytes of constants", None),
]


def format_text(numbers, connection_text=""):
    """The profile as the aligned text `ccdb db readiness` prints"""
    config, groups = numbers["config"], numbers
    totals = {"columns": groups["metadata"]["columns"], "tables": groups["metadata"]["tables"],
              "versions": groups["metadata"]["versions"], "constant_sets": groups["data"]["constant_sets"]}
    lines = []
    if connection_text:
        lines.append("Readiness profile of " + connection_text)
    lines.append("generated {0}, CCDB {1}, schema {2}".format(config["generated"], config["ccdb_version"], config["schema_version"]))
    lines.append("stale: no version created since {0} ({1} years)".format(config["stale_before"][:10], config["stale_years"]))
    lines.append("")
    for group, field, label, total_name in TEXT_ROWS:
        value = groups[group][field]
        if value is None:
            lines.append("  {0:<42} {1:>12}".format(label, "not measured"))
        elif total_name:
            total = totals[total_name]
            share = "{0:6.1f} %".format(100.0 * value / total) if total else "      -"
            lines.append("  {0:<42} {1:>12,} of {2:<12,} {3}".format(label, value, total, share))
        else:
            lines.append("  {0:<42} {1:>12,}".format(label, value))
    lines.append("")
    instance = groups["instance"]
    lines.append("  instance properties set: " + (", ".join(name for name in INSTANCE_PROPERTIES if instance[name]) or "none"))
    missing = [name for name in INSTANCE_PROPERTIES if not instance[name]]
    if missing:
        lines.append("  instance properties not set: " + ", ".join(missing))
    return "\n".join(lines)
