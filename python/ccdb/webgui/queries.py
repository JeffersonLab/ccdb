"""Query helpers for the table pages: one bounded SQL query per page plus a count, returned as dataclasses.

Views render these objects; a JSON view is `dataclasses.asdict` away. The only Flask-flavoured piece
is parse_page_query(), which reads a request's argument mapping and raises BadRequest.

Parameter policy: a value that is not a whole number, out of range, or a sort column or order the
page does not have, is a 400; a `per_page` outside PAGE_SIZES snaps to the nearest allowed size; a
`page` past the end is clamped to the last page, so a stale link lands on rows instead of on an
empty table, and no request turns into an OFFSET that walks the whole table.
"""
import math
import re
from urllib.parse import quote
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import case, func, or_, select
from sqlalchemy.orm import aliased
from werkzeug.exceptions import BadRequest

from ccdb.model import Assignment, ConstantSet, LogRecord, Property, RunRange, Tag, TypeTable, User, Variation
from ccdb.path_utils import format_request_time, local_to_utc

PAGE_SIZES = (25, 50, 100, 200)
DEFAULT_PAGE_SIZE = 50
INFINITE_RUN = 2147483647


@dataclass
class PageQuery:
    """What the user asked for: which page, how many rows, sorted how, filtered by what text."""
    page: int = 1
    per_page: int = DEFAULT_PAGE_SIZE
    sort: str = ""
    order: str = "desc"
    search: str = ""

    @property
    def offset(self):
        return (self.page - 1) * self.per_page


@dataclass
class Page:
    """One page of rows plus what a template needs for navigation."""
    items: list
    query: PageQuery
    total: int

    @property
    def page(self):
        return self.query.page

    @property
    def pages(self):
        return max(1, math.ceil(self.total / self.query.per_page))

    @property
    def first_row(self):
        return self.query.offset + 1 if self.items else 0

    @property
    def last_row(self):
        return self.query.offset + len(self.items)

    @property
    def has_prev(self):
        return self.query.page > 1

    @property
    def has_next(self):
        return self.query.page < self.pages


@dataclass
class AssignmentRow:
    id: int
    run_min: int
    run_max: int
    created: datetime
    variation: str
    author: str
    comment: str
    request: str  # the CCDB request string, identical to Assignment.request
    constant_set_id: int
    variation_deprecated: bool
    shared: int = 1  # how many assignments use this row's constant set; more than 1 is shared data


@dataclass
class LogRow:
    id: int
    created: datetime
    action: str
    description: str
    comment: str
    author: str


@dataclass
class LogRecordDetail:
    """One log record in full, for its own page; `affected` lists the (kind, id) pairs the record names."""
    id: int
    created: datetime
    action: str
    description: str
    comment: str
    author: str
    affected: list


@dataclass
class VariationRow:
    id: int
    name: str
    created: datetime
    comment: str
    parent: str
    author: str
    is_deprecated: bool = False
    deprecated_time: datetime = None
    deprecation_comment: str = ""
    deprecated_by: str = ""


@dataclass
class Activity:
    """How much a table, or the tables under a directory, has been used: the assignment count and the newest assignment."""
    assignments: int
    last_created: datetime = None
    last_author: str = ""


def integer_arg(args, name, default=None, minimum=None, maximum=None):
    """An integer request argument; empty means default; text that is not a number, or a value outside
    [minimum, maximum], is a 400.

    Bound every argument that reaches a query. Python integers have no width, but the database columns do:
    a run number past the 32-bit range reaches the driver and raises there, which answers 500 instead of 400.
    """
    raw = args.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise BadRequest("'{0}' must be a whole number, got '{1}'".format(name, raw))
    if minimum is not None and value < minimum:
        raise BadRequest("'{0}' must be at least {1}, got {2}".format(name, minimum, value))
    if maximum is not None and value > maximum:
        raise BadRequest("'{0}' must be at most {1}, got {2}".format(name, maximum, value))
    return value


def run_arg(args, name):
    """A run-number argument: a whole number from 0 to the open-ended run sentinel, the widest value the
    `runRanges` columns hold."""
    return integer_arg(args, name, minimum=0, maximum=INFINITE_RUN)


def parse_page_query(args, sort_columns, default_sort, default_order="desc"):
    """Reads page, per_page, sort, order and search from a request's args; see the module policy."""
    page = integer_arg(args, "page", default=1, minimum=1)
    wanted_size = integer_arg(args, "per_page", default=DEFAULT_PAGE_SIZE, minimum=1)
    per_page = min(PAGE_SIZES, key=lambda size: abs(size - wanted_size))
    sort = args.get("sort") or default_sort
    if sort not in sort_columns:
        raise BadRequest("'sort' must be one of {0}, got '{1}'".format(", ".join(sort_columns), sort))
    order = args.get("order") or default_order
    if order not in ("asc", "desc"):
        raise BadRequest("'order' must be 'asc' or 'desc', got '{0}'".format(order))
    return PageQuery(page=page, per_page=per_page, sort=sort, order=order, search=(args.get("search") or "").strip())


def run_page(session, statement, query, sort_columns, tiebreak, row_factory, count_statement=None):
    """Runs the count and the bounded data query for `statement` and wraps the rows.

    `statement` is a select() with its joins and filters already applied and no ORDER BY.
    `tiebreak` is a column that makes the order total, so paging never repeats or skips a row.
    `count_statement` counts without the joins when the filters allow it. Trap: counting over
    `statement.subquery()` makes MySQL materialize every joined row first — 1 s for the 820 000
    log records on hallddb — so a list function over a big table passes its own count.
    """
    if count_statement is None:
        count_statement = select(func.count()).select_from(statement.subquery())
    total = session.execute(count_statement).scalar_one()
    # The page number is clamped here, not in parse_page_query(), because the row count is what bounds it.
    # Without the clamp, `?page=10000000` becomes an OFFSET the database walks row by row before returning
    # nothing, and a value past the platform integer width reaches the driver and raises.
    query.page = min(query.page, max(1, math.ceil(total / query.per_page)))
    sort_column = sort_columns[query.sort]
    ordered = statement.order_by(sort_column.asc() if query.order == "asc" else sort_column.desc(),
                                 tiebreak.asc() if query.order == "asc" else tiebreak.desc())
    rows = session.execute(ordered.limit(query.per_page).offset(query.offset)).all()
    return Page(items=[row_factory(row) for row in rows], query=query, total=total)


def like_pattern(text):
    r"""A LIKE pattern matching `text` as a literal substring, for a like() call with escape="\".

    `%`, `_` and the escape character itself are escaped, so searching for `%` looks for a percent sign
    instead of matching every row — which on the production logs table means two full scans per request.
    Escape the backslash first, or escaping the wildcards would be undone. AlchemyProvider's search
    methods follow the same rule.
    """
    escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return "%{0}%".format(escaped)


def contains_text(columns, text):
    """Case-insensitive substring match on any of the columns (LIKE is case-insensitive on MySQL and for ASCII on SQLite)."""
    pattern = like_pattern(text)
    return or_(*[column.like(pattern, escape="\\") for column in columns])


def table_count(session):
    return session.execute(select(func.count()).select_from(TypeTable)).scalar_one()


# --------------------------------------------------------------------------- versions

ASSIGNMENT_SORTS = {
    "created": Assignment.created, "run_min": RunRange.min, "run_max": RunRange.max,
    "variation": Variation.name, "author": User.name, "id": Assignment.id,
}


def request_string(path, run_min, variation, created):
    """The CCDB request string, byte-identical to Assignment.request."""
    return "{0}:{1}:{2}:{3}".format(path, run_min, variation, format_request_time(created))


def list_assignments(session, table, query, variation=None, run=None, run_min=None, run_max=None, include_deprecated=True):
    """A page of a table's assignments, newest first by default.

    Filters: `variation` by exact name; `run` keeps the run ranges that contain it;
    `run_min`/`run_max` keep the run ranges that overlap that window; without `include_deprecated`,
    the assignments of deprecated variations are left out.
    """
    statement = (select(Assignment.id, RunRange.min, RunRange.max, Assignment.created, Variation.name, User.name, Assignment._comment,
                        Assignment.constant_set_id, Variation.is_deprecated)
                 .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id)
                 .join(RunRange, Assignment.run_range_id == RunRange.id)
                 .join(Variation, Assignment.variation_id == Variation.id)
                 .join(User, Assignment.author_id == User.id, isouter=True)
                 .where(ConstantSet.type_table_id == table.id))
    if variation:
        statement = statement.where(Variation.name == variation)
    if not include_deprecated:
        statement = statement.where(Variation.is_deprecated == False)  # noqa: E712 (SQL comparison)
    if run is not None:
        statement = statement.where(RunRange.min <= run, RunRange.max >= run)
    if run_min is not None:
        statement = statement.where(RunRange.max >= run_min)
    if run_max is not None:
        statement = statement.where(RunRange.min <= run_max)
    if query.search:
        statement = statement.where(contains_text([Assignment._comment, User.name], query.search))

    def row_factory(row):
        assignment_id, low, high, created, variation_name, author, comment, constant_set_id, variation_deprecated = row
        return AssignmentRow(assignment_id, low, high, created, variation_name, author or "", comment or "",
                             request_string(table.path, low, variation_name, created), constant_set_id, bool(variation_deprecated))

    page = run_page(session, statement, query, ASSIGNMENT_SORTS, Assignment.id, row_factory)
    counts = shared_counts(session, [row.constant_set_id for row in page.items])
    for row in page.items:
        row.shared = counts.get(row.constant_set_id, 1)
    return page


@dataclass
class Found:
    id: int
    request: str


def newest_before(session, table, run, variation_id, created, below_id):
    """The newest assignment (by id) of the table, run and variation with an id below `below_id` and created at or
    before `created`, or None: what a request for that moment resolved to before the assignment `below_id` existed.

    MAX(id) first, then that row: written as ORDER BY id DESC LIMIT 1 (AlchemyProvider.get_assignments), MariaDB walks
    the primary key back from the newest of all assignments until one matches, 0.55 s for /FCAL/gains on the Hall D
    database when the match is old; the aggregate goes through the table's sets and takes 7 ms.
    """
    newest_id = session.execute(select(func.max(Assignment.id))
                                .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id)
                                .join(RunRange, Assignment.run_range_id == RunRange.id)
                                .where(ConstantSet.type_table_id == table.id, Assignment.variation_id == variation_id,
                                       RunRange.min <= run, RunRange.max >= run, Assignment.created <= created,
                                       Assignment.id < below_id)).scalar_one()
    if newest_id is None:
        return None
    low, variation_name, created = session.execute(select(RunRange.min, Variation.name, Assignment.created)
                                                   .join(RunRange, Assignment.run_range_id == RunRange.id)
                                                   .join(Variation, Assignment.variation_id == Variation.id)
                                                   .where(Assignment.id == newest_id)).one()
    return Found(newest_id, request_string(table.path, low, variation_name, created))


def shared_counts(session, constant_set_ids):
    """{constant set id: number of assignments using it} for the given sets that more than one assignment uses.

    One query over the sets of one page, through the index on assignments.constantSetId. A count inside the page
    query would be a correlated subquery that MySQL may evaluate for every row of the table before the LIMIT.
    """
    if not constant_set_ids:
        return {}
    statement = (select(Assignment.constant_set_id, func.count())
                 .where(Assignment.constant_set_id.in_(sorted(set(constant_set_ids))))
                 .group_by(Assignment.constant_set_id)
                 .having(func.count() > 1))
    return dict(session.execute(statement).all())


SAME_DATA_LIMIT = 50  # links listed on the assignment page; a set shared more widely shows the total and the first ones


@dataclass
class SameData:
    """The other assignments that use an assignment's constant set, oldest first: (request string, id) pairs."""
    total: int  # other assignments, all of them
    items: list


def same_data(session, assignment, table_path):
    """The other assignments of the same constant set; two small indexed queries, the second only for shared data."""
    total = session.execute(select(func.count()).where(Assignment.constant_set_id == assignment.constant_set_id,
                                                       Assignment.id != assignment.id)).scalar_one()
    if not total:
        return SameData(0, [])
    rows = session.execute(select(Assignment.id, RunRange.min, Variation.name, Assignment.created)
                           .join(RunRange, Assignment.run_range_id == RunRange.id)
                           .join(Variation, Assignment.variation_id == Variation.id)
                           .where(Assignment.constant_set_id == assignment.constant_set_id, Assignment.id != assignment.id)
                           .order_by(Assignment.created, Assignment.id)
                           .limit(SAME_DATA_LIMIT)).all()
    return SameData(total, [(request_string(table_path, low, variation_name, created), assignment_id)
                            for assignment_id, low, variation_name, created in rows])


def assignment_activity(session, table_ids):
    """The number of assignments over the tables and the newest one (date and author); two bounded queries.

    Serves the info boxes of the tree. A table's `modified` column never changes after creation, so the
    newest assignment is what tells when a table was last worked on.
    """
    table_ids = list(table_ids)
    if not table_ids:
        return Activity(0)
    on_tables = ConstantSet.type_table_id.in_(table_ids)
    count = session.execute(select(func.count(Assignment.id))
                            .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id).where(on_tables)).scalar_one()
    if not count:
        return Activity(0)
    # ORDER BY created DESC LIMIT 1 walks the index on `created` backwards and stops at the first match
    # (50 ms on hallddb for a directory with 300 000 assignments); MAX(created) over the same join reads
    # every row instead (8 s cold). Keep the ORDER BY form.
    newest = session.execute(select(Assignment.created, User.name)
                             .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id)
                             .join(User, Assignment.author_id == User.id, isouter=True)
                             .where(on_tables).order_by(Assignment.created.desc(), Assignment.id.desc()).limit(1)).first()
    return Activity(count, newest[0], newest[1] or "")


def table_variation_names(session, table, include_deprecated=True):
    """Names of the variations that have at least one assignment on the table, for the filter select."""
    statement = (select(Variation.name).distinct()
                 .join(Assignment, Assignment.variation_id == Variation.id)
                 .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id)
                 .where(ConstantSet.type_table_id == table.id).order_by(Variation.name))
    if not include_deprecated:
        statement = statement.where(Variation.is_deprecated == False)  # noqa: E712 (SQL comparison)
    return [row[0] for row in session.execute(statement)]


# --------------------------------------------------------------------------- logs

LOG_SORTS = {"created": LogRecord.created, "action": LogRecord.action, "author": User.name, "id": LogRecord.id}


def list_logs(session, query):
    """A page of log records, newest first by default; search matches description and author.

    The author match is `author_id IN (users whose name matches)` rather than a LIKE on the joined
    column, and the count runs on the logs table alone, so the users join never multiplies the scan.
    """
    statement = (select(LogRecord.id, LogRecord.created, LogRecord.action, LogRecord.description, LogRecord.comment, User.name)
                 .join(User, LogRecord.author_id == User.id, isouter=True))
    count_statement = select(func.count()).select_from(LogRecord)
    if query.search:
        pattern = like_pattern(query.search)
        matching_authors = select(User.id).where(User.name.like(pattern, escape="\\"))
        condition = or_(LogRecord.description.like(pattern, escape="\\"), LogRecord.author_id.in_(matching_authors))
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    return run_page(session, statement, query, LOG_SORTS, LogRecord.id,
                    lambda row: LogRow(row[0], row[1], row[2], row[3] or "", row[4] or "", row[5] or ""), count_statement)


AFFECTED_OBJECT = re.compile(r"(assignments|variations|typeTables|directories|users)_?(\d+)")


def parse_affected(text):
    """The (kind, id) pairs of a record's affectedIds column: `|assignments812174|` and the oldest records' `users_1`."""
    return [(kind, int(number)) for kind, number in AFFECTED_OBJECT.findall(text or "")]


def log_record(session, log_id):
    """One log record with its author, or None: a primary-key read."""
    row = session.execute(select(LogRecord.id, LogRecord.created, LogRecord.action, LogRecord.description, LogRecord.comment, User.name, LogRecord.affected_ids)
                          .join(User, LogRecord.author_id == User.id, isouter=True).where(LogRecord.id == log_id)).first()
    if row is None:
        return None
    return LogRecordDetail(row[0], row[1], row[2], row[3] or "", row[4] or "", row[5] or "", parse_affected(row[6]))


# --------------------------------------------------------------------------- variations

VARIATION_SORTS = {"id": Variation.id, "name": Variation.name, "created": Variation.created}


def list_variations(session, query, include_deprecated=True):
    """A page of variations with their parent's name and the deprecation fields; search matches name and comment."""
    parent = aliased(Variation)
    deprecated_by = aliased(User)
    statement = (select(Variation.id, Variation.name, Variation.created, Variation.comment, parent.name, User.name,
                        Variation.is_deprecated, Variation.deprecated_time, Variation.deprecation_comment, deprecated_by.name)
                 .join(parent, Variation.parent_id == parent.id, isouter=True)
                 .join(User, Variation.author_id == User.id, isouter=True)
                 .join(deprecated_by, Variation.deprecated_by_user_id == deprecated_by.id, isouter=True))
    if not include_deprecated:
        statement = statement.where(Variation.is_deprecated == False)  # noqa: E712 (SQL comparison)
    if query.search:
        statement = statement.where(contains_text([Variation.name, Variation.comment], query.search))
    return run_page(session, statement, query, VARIATION_SORTS, Variation.id,
                    lambda row: VariationRow(row[0], row[1], row[2], row[3] or "", row[4] or "", row[5] or "",
                                             bool(row[6]), row[7], row[8] or "", row[9] or ""))


def variation_ids(session):
    """name -> id for every variation; one query."""
    return {name: variation_id for name, variation_id in session.execute(select(Variation.name, Variation.id))}


def affected_tables(session, variation_ids, run=None, before=None):
    """The tables with assignments in the variations: {table id: {variation id: (count, newest created)}}.

    `run` keeps the assignments whose run range contains it; `before` keeps the ones created up to that
    moment, the way a request with a timestamp resolves. One grouped query over the index on variationId;
    its cost grows with the assignments of the variations (0.4 s for 85 000 on hallddb), so the root
    variation, which owns most assignments, is never passed here.
    """
    statement = (select(Assignment.variation_id, ConstantSet.type_table_id, func.count(Assignment.id), func.max(Assignment.created))
                 .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id)
                 .where(Assignment.variation_id.in_(list(variation_ids))))
    if run is not None:
        statement = statement.join(RunRange, Assignment.run_range_id == RunRange.id).where(RunRange.min <= run, RunRange.max >= run)
    if before is not None:
        statement = statement.where(Assignment.created <= before)
    grouped = {}
    for variation_id, table_id, count, newest in session.execute(statement.group_by(Assignment.variation_id, ConstantSet.type_table_id)):
        grouped.setdefault(table_id, {})[variation_id] = (count, newest)
    return grouped


def deprecated_variation_names(session):
    return set(session.execute(select(Variation.name).where(Variation.is_deprecated == True)).scalars())  # noqa: E712 (SQL comparison)


# --------------------------------------------------------------------------- properties

def properties_of(session, owner_type, owner_ids):
    """{owner id: [(name, value), ...] by name} for the owners of one kind (`ccdb prop`); owners without properties are absent.
    The instance's own properties have owner type 'instance' and owner id 0."""
    if not owner_ids:
        return {}
    statement = (select(Property.owner_id, Property.name, Property.value)
                 .where(Property.owner_type == owner_type, Property.owner_id.in_(sorted(set(owner_ids))))
                 .order_by(Property.owner_id, Property.name))
    found = {}
    for owner_id, name, value in session.execute(statement):
        found.setdefault(owner_id, []).append((name, value))
    return found


# --------------------------------------------------------------------------- tags

@dataclass
class TagRow:
    name: str
    variation: str
    snapshot_time: datetime  # a UTC instant
    comment: str
    author: str
    created: datetime
    id: int = 0


def list_tags(session):
    """Every tag by name; tags are few (a handful per run period), so the list has no pages."""
    statement = (select(Tag.name, Variation.name, Tag.snapshot_time, Tag.comment, User.name, Tag.created, Tag.id)
                 .join(Variation, Tag.variation_id == Variation.id)
                 .join(User, Tag.author_id == User.id, isouter=True)
                 .order_by(Tag.name))
    return [TagRow(name, variation, snapshot, comment or "", author or "", created, tag_id)
            for name, variation, snapshot, comment, author, created, tag_id in session.execute(statement)]


@dataclass
class Resolved:
    """What a request `table:run@tag` returns for one table."""
    assignment_id: int
    run_min: int
    variation: str
    created: datetime


def tag_resolution(session, variation_ids, run, created_condition):
    """{table id: Resolved} for every table that a request with the tag answers for `run`.

    `variation_ids` is the tag's variation and its parents, nearest first; `created_condition` the tag's time limit as
    the provider builds it. Per table, the nearest variation with an assignment wins, and in it the newest by id: the
    rule of AlchemyProvider.get_assignment, in one query over every table (ROW_NUMBER, MySQL 8, MariaDB 10.2, SQLite 3.25).
    """
    depth = case({variation_id: level for level, variation_id in enumerate(variation_ids)}, value=Assignment.variation_id)
    ranked = (select(ConstantSet.type_table_id.label("table_id"), Assignment.id.label("assignment_id"), RunRange.min.label("run_min"),
                     Variation.name.label("variation"), Assignment.created.label("created"),
                     func.row_number().over(partition_by=ConstantSet.type_table_id, order_by=(depth, Assignment.id.desc())).label("rank"))
              .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id)
              .join(RunRange, Assignment.run_range_id == RunRange.id)
              .join(Variation, Assignment.variation_id == Variation.id)
              .where(Assignment.variation_id.in_(variation_ids), RunRange.min <= run, RunRange.max >= run, created_condition)
              .subquery())
    rows = session.execute(select(ranked.c.table_id, ranked.c.assignment_id, ranked.c.run_min, ranked.c.variation, ranked.c.created)
                           .where(ranked.c.rank == 1))
    return {table_id: Resolved(assignment_id, run_min, variation, created) for table_id, assignment_id, run_min, variation, created in rows}


def variation_chains(session):
    """name -> the ancestry from the root as a list, for example ['default', 'test', 'subtest']. Variations are few, one query."""
    rows = session.execute(select(Variation.id, Variation.name, Variation.parent_id)).all()
    by_id = {row[0]: (row[1], row[2]) for row in rows}
    chains = {}
    for variation_id, (name, _parent) in by_id.items():
        chain, current, seen = [], variation_id, set()
        while current in by_id and current not in seen:  # `seen` guards against a cycle in bad data
            seen.add(current)
            chain.append(by_id[current][0])
            current = by_id[current][1]
        chains[name] = list(reversed(chain))
    return chains


# --------------------------------------------------------------------------- data card

# Instance properties a card shows (`ccdb prop set --instance`), in this order
CARD_INSTANCE_PROPERTIES = ("experiment", "license", "citation", "contact", "url")


@dataclass
class CardVariation:
    """The assignments of one variation on a table: how many, and the runs they cover as merged intervals."""
    name: str
    versions: int
    runs: list


@dataclass
class TableCard:
    """What the data card of a table shows (GUI /tables/<path>/card, API /api/v1/tables/<path>/card). Times are the
    model's: assignment creation times naive local wall times, tag times naive UTC."""
    table: TypeTable
    properties: list
    instance: list
    versions: int
    variations: list
    authors: list
    last_created: datetime = None
    last_author: str = ""
    last_variation: str = ""
    last_comment: str = ""
    tags: list = None


def card_jsonld(card):
    """The data card as a schema.org Dataset in JSON-LD, the form catalogs and search engines read (docs/concepts/fair.md).

    Served by the API (/tables/<path>/card?format=jsonld) and embedded in the GUI card page. The `url` is the card
    page under the instance property `url`, the published address of the web GUI, and is left out without it: an
    address taken from the request would differ behind a proxy and change the bytes a cache keeps."""
    table = card.table
    instance, properties = dict(card.instance), dict(card.properties)
    record = {"@context": "https://schema.org", "@type": "Dataset", "name": table.path, "identifier": table.path,
              "description": table.comment or properties.get("description") or "Calibration constants " + table.path,
              "isAccessibleForFree": True,
              "variableMeasured": []}
    for column in table.columns:
        variable = {"@type": "PropertyValue", "name": column.name}
        if column.units:
            variable["unitText"] = column.units
        if column.comment:
            variable["description"] = column.comment
        record["variableMeasured"].append(variable)
    if instance.get("url", "").startswith(("http://", "https://")):
        record["url"] = instance["url"].rstrip("/") + "/tables" + quote(table.path) + "/card"
    if card.authors:
        record["creator"] = [{"@type": "Person", "name": name} for name, _ in card.authors if name]
    if card.last_created is not None:
        record["dateModified"] = local_to_utc(card.last_created).strftime("%Y-%m-%dT%H:%M:%SZ")
    for key in ("license", "citation"):
        if properties.get(key) or instance.get(key):
            record[key] = properties.get(key) or instance[key]
    if properties.get("keywords"):
        record["keywords"] = [word.strip() for word in properties["keywords"].split(",") if word.strip()]
    if instance.get("experiment"):
        record["includedInDataCatalog"] = {"@type": "DataCatalog", "name": "CCDB of " + instance["experiment"]}
    return record


def merged_runs(ranges):
    """[(min, max)] merged into the fewest intervals that cover the same runs, sorted"""
    merged = []
    for low, high in sorted(ranges):
        if merged and low <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], high))
        else:
            merged.append((low, high))
    return merged


def table_card(db, table):
    """The data card of a table: its properties and the instance's, its columns (on the table object), its versions
    and run coverage per variation, its authors, its last change, and the tags under which it gives constants."""
    session = db.session
    rows = session.execute(
        select(Variation.name, RunRange.min, RunRange.max, User.name, Assignment.created, Assignment.__table__.c.comment)
        .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id)
        .join(Variation, Assignment.variation_id == Variation.id)
        .join(RunRange, Assignment.run_range_id == RunRange.id)
        .join(User, Assignment.author_id == User.id, isouter=True)
        .where(ConstantSet.type_table_id == table.id)
        .order_by(Assignment.created, Assignment.id)).all()

    ranges, authors = {}, {}
    for variation, run_min, run_max, author, _, _ in rows:
        ranges.setdefault(variation, []).append((run_min, run_max))
        authors[author or ""] = authors.get(author or "", 0) + 1
    variations = [CardVariation(name, len(found), merged_runs(found)) for name, found in sorted(ranges.items())]
    card = TableCard(table=table, properties=properties_of(session, "table", [table.id]).get(table.id, []),
                     instance=[(name, value) for name, value in properties_of(session, "instance", [0]).get(0, [])
                               if name in CARD_INSTANCE_PROPERTIES],
                     versions=len(rows), variations=variations,
                     authors=sorted(authors.items(), key=lambda item: (-item[1], item[0])), tags=[])
    card.instance.sort(key=lambda item: CARD_INSTANCE_PROPERTIES.index(item[0]))
    if rows:
        newest = rows[-1]
        card.last_created, card.last_author, card.last_variation, card.last_comment = newest[4], newest[3] or "", newest[0], newest[5] or ""

    # A tag covers the table when its variation, or a parent of it, has an assignment of the table made before its time
    for tag_row in list_tags(session):
        tag = db.get_tag(tag_row.name)
        variation_ids = [variation.id for variation in db.get_variation_tree_up(db.get_tag_variation(tag))]
        found = session.execute(select(Assignment.id)
                                .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id)
                                .where(ConstantSet.type_table_id == table.id, Assignment.variation_id.in_(variation_ids),
                                       db._created_at_or_before(tag.snapshot_time)).limit(1)).first()
        if found:
            card.tags.append(tag_row)
    return card
