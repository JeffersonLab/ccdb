"""The read-only service functions of the HTTP API and the MCP server: plain functions of a provider and parameters
that return the API's models (ccdb.api.models). The HTTP routes (browse.py, constants.py) and the MCP tools wrap
them, so both answer from the same code and with the same values.

The queries are the web GUI's (ccdb.webgui.queries, ccdb.webgui.assignments), so the GUI, the API and the MCP
server show the same rows. Errors: ObjectIsNotFoundInDbError or LookupError for an object that does not exist,
ValueError for a malformed parameter; the GUI helpers raise werkzeug's HTTP errors, which carry the same codes.
"""
import dataclasses
import datetime
import json

from sqlalchemy import select

from ccdb import version as ccdb_version_module
from ccdb.errors import ObjectIsNotFoundInDbError
from ccdb.model import RunRange, User, Variation
from ccdb.path_utils import local_to_utc, parse_request
from ccdb.webgui import assignments as gui_assignments
from ccdb.webgui import diff
from ccdb.webgui import queries

from . import models

ccdb_version = ccdb_version_module.version


# ---------------------------------------------------------------------------------------------------------- values

def utc_text(local_time):
    """A naive local wall time, as the model gives it, as an ISO 8601 UTC instant with microseconds"""
    if local_time is None:
        return None
    return local_to_utc(local_time).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def utc_text_of_utc(naive_utc):
    """A naive UTC value (tags.snapshotTime) as an ISO 8601 UTC instant"""
    return naive_utc.replace(tzinfo=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def include_deprecated(deprecated):
    """`deprecated=all` as True; absent as False; anything else is an error"""
    if deprecated not in (None, "", "all"):
        raise ValueError("'deprecated' must be 'all' or absent, got '{0}'".format(deprecated))
    return deprecated == "all"


def deprecation(obj):
    return dict(deprecated=bool(obj.is_deprecated), deprecated_time=utc_text(obj.deprecated_time),
                deprecation_comment=obj.deprecation_comment)


def author_name(db, author_id):
    user = db.session.get(User, author_id) if author_id else None
    return user.name if user is not None else ""


def properties(db, owner_type, owner_id):
    return dict(queries.properties_of(db.session, owner_type, [owner_id]).get(owner_id, []))


def directory_summary(directory):
    return models.DirectorySummary(path=directory.path, name=directory.name, comment=directory.comment or "", **deprecation(directory))


def table_summary(table):
    return models.TableSummary(path=table.path, name=table.name, rows=table.rows_count, column_count=table.columns_count,
                               comment=table.comment or "", **deprecation(table))


def columns_of(table):
    return [models.Column(name=column.name, type=column.type, units=column.units or None, comment=column.comment or "")
            for column in table.columns]


# ---------------------------------------------------------------------------------------------------------- browse

def instance(db):
    return models.Instance(version=ccdb_version, schema_version=6, properties=properties(db, "instance", 0))


def directories(db, show_deprecated=False):
    """Every directory below the root, by path; a deprecated directory hides its subtree, as in `ccdb ls`"""
    found, waiting = [], list(db.get_root_directory().sub_dirs)
    while waiting:
        directory = waiting.pop()
        if show_deprecated or not directory.is_deprecated:
            found.append(directory)
            waiting.extend(directory.sub_dirs)
    return [directory_summary(each) for each in sorted(found, key=lambda each: each.path)]


def directory(db, path, show_deprecated=False):
    found = db.get_directory("/" + path.strip("/"))
    subdirectories = [each for each in found.sub_dirs if show_deprecated or not each.is_deprecated]
    tables = [each for each in found.type_tables if show_deprecated or not each.is_deprecated]
    return models.DirectoryInfo(path=found.path, name=found.name, comment=found.comment or "", **deprecation(found),
                                created=utc_text(found.created), modified=utc_text(found.modified),
                                author=author_name(db, found.author_id), properties=properties(db, "directory", found.id),
                                directories=[directory_summary(each) for each in sorted(subdirectories, key=lambda each: each.name)],
                                tables=[table_summary(each) for each in sorted(tables, key=lambda each: each.name)])


def tables(db, search="*", show_deprecated=False):
    db.get_root_directory()        # loads the directories, so every table path is complete
    found = [each for each in db.search_type_tables(search or "*") if show_deprecated or not each.is_deprecated]
    return [table_summary(each) for each in sorted(found, key=lambda each: each.path)]


def table_object(db, path):
    db.get_root_directory()
    return db.get_type_table("/" + path.strip("/"))     # unknown → ObjectIsNotFoundInDbError


def table(db, path):
    found = table_object(db, path)
    activity = queries.assignment_activity(db.session, [found.id])
    return models.TableInfo(path=found.path, name=found.name, rows=found.rows_count, column_count=found.columns_count,
                            comment=found.comment or "", **deprecation(found), created=utc_text(found.created),
                            modified=utc_text(found.modified), author=author_name(db, found.author_id), columns=columns_of(found),
                            properties=properties(db, "table", found.id), variations=queries.table_variation_names(db.session, found),
                            assignments=activity.assignments, last_assignment=utc_text(activity.last_created),
                            last_author=activity.last_author)


def table_card(db, path):
    """The data card of a table, from the GUI's card builder"""
    card = queries.table_card(db, table_object(db, path))
    table = card.table
    instance = dict(card.instance)
    last = None
    if card.last_created is not None:
        last = models.CardChange(created=utc_text(card.last_created), author=card.last_author, variation=card.last_variation,
                                 comment=card.last_comment)
    return models.TableCard(path=table.path, name=table.name, description=table.comment or "", deprecated=bool(table.is_deprecated),
                            rows=table.rows_count, columns=columns_of(table), properties=dict(card.properties),
                            versions=card.versions,
                            variations=[models.CardVariation(name=each.name, versions=each.versions, runs=[list(run) for run in each.runs])
                                        for each in card.variations],
                            authors=[{"name": name, "assignments": count} for name, count in card.authors],
                            last_change=last, tags=[tag.name for tag in card.tags], license=instance.get("license", ""),
                            citation=instance.get("citation", ""), instance=instance)


# JSON Schema of the cells of data.json: CCDB keeps every cell as the text it was given, so every cell is a string;
# the column type says how to read it
CELL_PATTERNS = {"int": r"^[+-]?[0-9]+$", "uint": r"^\+?[0-9]+$", "long": r"^[+-]?[0-9]+$", "ulong": r"^\+?[0-9]+$",
                 "bool": r"^(true|false|0|1)$"}


def table_schema(db, path, schema_id=None):
    """A JSON Schema (2020-12) of the `rows` of the table's data.json"""
    found = table_object(db, path)
    cells = []
    for column in found.columns:
        cell = {"type": "string", "title": column.name, "x-ccdb-type": column.type}
        description = (column.comment or "").strip()
        if column.units:
            cell["x-ccdb-units"] = column.units
            description = "{0} [{1}]".format(description, column.units).strip()
        if description:
            cell["description"] = description
        if column.type in CELL_PATTERNS:
            cell["pattern"] = CELL_PATTERNS[column.type]
        cells.append(cell)
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "title": found.path, "description": found.comment or "",
              "type": "array", "minItems": found.rows_count, "maxItems": found.rows_count,
              "items": {"type": "array", "prefixItems": cells, "items": False, "minItems": len(cells), "maxItems": len(cells)}}
    if schema_id:
        schema["$id"] = schema_id
    return schema


def versions(db, path, args, variation=None, run=None, run_min=None, run_max=None, show_deprecated=False):
    """A page of a table's assignments; `args` holds page, per_page, sort and order (a mapping with .get)"""
    found_table = table_object(db, path)
    query = queries.parse_page_query(args, queries.ASSIGNMENT_SORTS, default_sort="created")
    page = queries.list_assignments(db.session, found_table, query, variation=variation, run=run, run_min=run_min, run_max=run_max,
                                    include_deprecated=show_deprecated)
    items = [models.AssignmentRow(id=row.id, request=row.request, run_min=row.run_min, run_max=row.run_max, variation=row.variation,
                                  created=utc_text(row.created), author=row.author, comment=row.comment, shared_by=row.shared)
             for row in page.items]
    return models.AssignmentPage(items=items, page=page.page, per_page=page.query.per_page, pages=page.pages, total=page.total,
                                 sort=page.query.sort, order=page.query.order)


def variation_model(db, variation, chains):
    return models.Variation(name=variation.name, comment=variation.comment or "",
                            parent=variation.parent.name if variation.parent is not None and variation.parent_id != variation.id else None,
                            chain=chains.get(variation.name, [variation.name]), created=utc_text(variation.created),
                            author=author_name(db, variation.author_id), **deprecation(variation))


def variations(db, show_deprecated=False):
    chains = queries.variation_chains(db.session)
    found = db.session.execute(select(Variation).order_by(Variation.name)).scalars().all()
    return [variation_model(db, each, chains) for each in found if show_deprecated or not each.is_deprecated]


def variation(db, name):
    return variation_model(db, db.get_variation(name), queries.variation_chains(db.session))


def run_ranges(db):
    found = db.session.execute(select(RunRange).order_by(RunRange.min, RunRange.max, RunRange.id)).scalars().all()
    return [models.RunRange(id=each.id, name=each.name or "", min=each.min, max=each.max, comment=each.comment or "") for each in found]


def tag_model(row):
    return models.Tag(name=row.name, variation=row.variation, time=utc_text_of_utc(row.snapshot_time), comment=row.comment,
                      author=row.author, created=utc_text(row.created))


def tags(db):
    return [tag_model(row) for row in queries.list_tags(db.session)]


def tag(db, name):
    rows = [row for row in queries.list_tags(db.session) if row.name == name]
    if not rows:
        raise ObjectIsNotFoundInDbError(models.Tag, "No tag '{0}'".format(name))
    return tag_model(rows[0])


def logs(db, args):
    """A page of the change log; `args` holds page, per_page, sort, order and search"""
    query = queries.parse_page_query(args, queries.LOG_SORTS, default_sort="id")
    page = queries.list_logs(db.session, query)
    items = [models.LogRow(id=row.id, created=utc_text(row.created), action=row.action, description=row.description,
                           comment=row.comment, author=row.author) for row in page.items]
    return models.LogPage(items=items, page=page.page, per_page=page.query.per_page, pages=page.pages, total=page.total,
                          sort=page.query.sort, order=page.query.order)


ATOM = "http://www.w3.org/2005/Atom"


def logs_atom(db, args, feed_url, record_url):
    """The newest page of the change log as an Atom feed (RFC 4287): one entry per log record, newest first.
    `args` takes per_page and search as /logs does; record_url(id) gives an entry's link"""
    from xml.etree import ElementTree
    query = queries.parse_page_query(args, queries.LOG_SORTS, default_sort="id")
    page = queries.list_logs(db.session, dataclasses.replace(query, page=1, sort="id", order="desc"))
    experiment = dict(queries.properties_of(db.session, "instance", [0]).get(0, [])).get("experiment", "")
    ElementTree.register_namespace("", ATOM)

    def element(parent, name, text=None, **attributes):
        child = ElementTree.SubElement(parent, "{%s}%s" % (ATOM, name), attributes)
        if text is not None:
            child.text = text
        return child

    feed = ElementTree.Element("{%s}feed" % ATOM)
    element(feed, "id", feed_url)
    element(feed, "title", "CCDB changes" + (" · " + experiment if experiment else "") + (" · " + query.search if query.search else ""))
    newest = page.items[0].created if page.items else None
    element(feed, "updated", utc_text(newest) if newest else "1970-01-01T00:00:00.000000Z")
    element(feed, "link", rel="self", href=feed_url)
    element(feed, "generator", "CCDB " + ccdb_version)
    for row in page.items:
        entry = element(feed, "entry")
        url = record_url(row.id)
        element(entry, "id", url)
        element(entry, "title", "{0}: {1}".format(row.action, row.description))
        element(entry, "updated", utc_text(row.created))
        element(element(entry, "author"), "name", row.author or "unknown")
        element(entry, "link", rel="alternate", href=url)
        element(entry, "category", term=row.action)
        if row.comment:
            element(entry, "summary", row.comment)
    return ElementTree.tostring(feed, encoding="unicode", xml_declaration=True)


def log_record(db, log_id):
    found = queries.log_record(db.session, log_id)
    if found is None:
        raise ObjectIsNotFoundInDbError(models.LogRecord, "No log record {0}".format(log_id))
    return models.LogRecord(id=found.id, created=utc_text(found.created), action=found.action, description=found.description,
                            comment=found.comment, author=found.author, affected=[list(pair) for pair in found.affected])


# ---------------------------------------------------------------------------------------------------------- assignments

def names_for_good(request_string):
    """Whether a request string names one assignment for good: a tag, or a time in the past"""
    parsed = parse_request(request_string)
    return parsed.tag_is_parsed or (parsed.time_is_parsed and parsed.time <= datetime.datetime.now())


def resolve(db, request_string=None, assignment_id=None):
    """(assignment, named for good) for a database id or a request string; malformed → 400, unknown → 404"""
    if assignment_id is None and not request_string:
        raise ValueError("Give an assignment id or a request string: /path:run:variation:time or /path:run@tag")
    resolved = gui_assignments.resolve_assignment(db, request_string, assignment_id)
    return resolved.assignment, assignment_id is not None or names_for_good(request_string)


def resolve_side(db, value):
    """A comparison side, a database id or a request string, as (assignment, named for good)"""
    value = (value or "").strip()
    if not value:
        raise ValueError("Both sides are needed: a request string or a database id each")
    if value.isdigit():
        return resolve(db, assignment_id=int(value))
    return resolve(db, request_string=value)


def assignment(db, found):
    """The metadata of an assignment, with the stored hash and size of its data"""
    found_table = found.constant_set.type_table
    shared = queries.shared_counts(db.session, [found.constant_set_id]).get(found.constant_set_id, 1)
    return models.Assignment(id=found.id, request=found.request, table=found_table.path, variation=found.variation.name,
                             run_min=found.run_range.min, run_max=found.run_range.max, created=utc_text(found.created),
                             author=found.author.name if found.author else "", comment=found.comment,
                             sha256=found.constant_set.sha256, size=found.constant_set.size,
                             rows=found_table.rows_count, columns=columns_of(found_table), shared_by=shared)


def data_json(found):
    """The data.json text of an assignment, byte-identical to the web GUI's"""
    return json.dumps(gui_assignments.assignment_dict(found), ensure_ascii=False, sort_keys=True, indent=1)


def data_text(found):
    """The `ccdb dump` text of an assignment, byte-identical to the web GUI's data.txt"""
    return gui_assignments.assignment_text(found)


def compare_pair(db, a, b):
    """(assignment a, assignment b, both named for good) of one table"""
    side_a, exact_a = resolve_side(db, a)
    side_b, exact_b = resolve_side(db, b)
    if side_a.constant_set.type_table.id != side_b.constant_set.type_table.id:
        raise ValueError("The sides belong to different tables: {0} and {1}".format(side_a.constant_set.type_table.path,
                                                                                  side_b.constant_set.type_table.path))
    return side_a, side_b, exact_a and exact_b


def comparison(side_a, side_b):
    columns = [{"name": column.name, "type": column.type} for column in side_a.constant_set.type_table.columns]
    return diff.diff_tables(side_a.constant_set.data_table, side_b.constant_set.data_table, columns)


def compare(side_a, side_b, changed_only=False):
    """The comparison as the web GUI's compare/data.json gives it"""
    result = comparison(side_a, side_b)
    body = {"table": side_a.constant_set.type_table.path, "columns": result.columns, "cells": result.cells,
            "changed_cells": result.changed_cells, "changed_rows": result.changed_rows, "changed_only": bool(changed_only),
            "rows": [{"row": row_i, "cells": [{"a": cell.a, "b": cell.b, "changed": cell.changed} for cell in cells]}
                     for row_i, cells in diff.kept_rows(result, bool(changed_only))]}
    for side, each in (("a", side_a), ("b", side_b)):
        body[side] = {key: value for key, value in gui_assignments.assignment_dict(each).items() if key not in ("columns", "rows", "table")}
    return body


def compare_diff(side_a, side_b):
    """The comparison as a unified diff, as the web GUI's compare/data.diff gives it"""
    labels = ["{0}, id {1}, created {2}".format(side, each.id, each.created) for side, each in (("A", side_a), ("B", side_b))]
    return "\n".join(diff.unified_diff(comparison(side_a, side_b), side_a.request, side_b.request, *labels)) + "\n"
