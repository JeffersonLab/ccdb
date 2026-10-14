"""Query helpers for the table pages: one bounded SQL query per page plus a count, returned as dataclasses.

Views render these objects; a JSON view is `dataclasses.asdict` away. The only Flask-flavoured piece
is parse_page_query(), which reads a request's argument mapping and raises BadRequest.

Parameter policy: a value that is not a whole number, or a sort column or order the page does not
have, is a 400; a `per_page` outside PAGE_SIZES snaps to the nearest allowed size; a `page` past the
end gives an empty page with navigation, so a stale link still renders.
"""
import math
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import aliased
from werkzeug.exceptions import BadRequest

from ccdb.model import Assignment, ConstantSet, LogRecord, RunRange, User, Variation

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


@dataclass
class LogRow:
    id: int
    created: datetime
    action: str
    description: str
    comment: str
    author: str


@dataclass
class VariationRow:
    id: int
    name: str
    created: datetime
    comment: str
    parent: str
    author: str


def integer_arg(args, name, default=None, minimum=None):
    """An integer request argument; empty means default; text that is not a number is a 400."""
    raw = args.get(name)
    if raw in (None, ""):
        return default
    try:
        value = int(raw)
    except ValueError:
        raise BadRequest("'{0}' must be a whole number, got '{1}'".format(name, raw))
    if minimum is not None and value < minimum:
        raise BadRequest("'{0}' must be at least {1}, got {2}".format(name, minimum, value))
    return value


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
    sort_column = sort_columns[query.sort]
    ordered = statement.order_by(sort_column.asc() if query.order == "asc" else sort_column.desc(),
                                 tiebreak.asc() if query.order == "asc" else tiebreak.desc())
    rows = session.execute(ordered.limit(query.per_page).offset(query.offset)).all()
    return Page(items=[row_factory(row) for row in rows], query=query, total=total)


def contains_text(columns, text):
    """Case-insensitive substring match on any of the columns (LIKE is case-insensitive on MySQL and for ASCII on SQLite)."""
    pattern = "%{0}%".format(text)
    return or_(*[column.like(pattern) for column in columns])


# --------------------------------------------------------------------------- versions

ASSIGNMENT_SORTS = {
    "created": Assignment.created, "run_min": RunRange.min, "run_max": RunRange.max,
    "variation": Variation.name, "author": User.name, "id": Assignment.id,
}


def request_string(path, run_min, variation, created):
    """The CCDB request string, byte-identical to Assignment.request."""
    return "{0}:{1}:{2}:{3}".format(path, run_min, variation, created.strftime("%Y-%m-%d_%H-%M-%S"))


def list_assignments(session, table, query, variation=None, run=None, run_min=None, run_max=None):
    """A page of a table's assignments, newest first by default.

    Filters: `variation` by exact name; `run` keeps the run ranges that contain it;
    `run_min`/`run_max` keep the run ranges that overlap that window.
    """
    statement = (select(Assignment.id, RunRange.min, RunRange.max, Assignment.created, Variation.name, User.name, Assignment._comment)
                 .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id)
                 .join(RunRange, Assignment.run_range_id == RunRange.id)
                 .join(Variation, Assignment.variation_id == Variation.id)
                 .join(User, Assignment.author_id == User.id, isouter=True)
                 .where(ConstantSet.type_table_id == table.id))
    if variation:
        statement = statement.where(Variation.name == variation)
    if run is not None:
        statement = statement.where(RunRange.min <= run, RunRange.max >= run)
    if run_min is not None:
        statement = statement.where(RunRange.max >= run_min)
    if run_max is not None:
        statement = statement.where(RunRange.min <= run_max)
    if query.search:
        statement = statement.where(contains_text([Assignment._comment, User.name], query.search))

    def row_factory(row):
        assignment_id, low, high, created, variation_name, author, comment = row
        return AssignmentRow(assignment_id, low, high, created, variation_name, author or "", comment or "",
                             request_string(table.path, low, variation_name, created))

    return run_page(session, statement, query, ASSIGNMENT_SORTS, Assignment.id, row_factory)


def table_variation_names(session, table):
    """Names of the variations that have at least one assignment on the table, for the filter select."""
    statement = (select(Variation.name).distinct()
                 .join(Assignment, Assignment.variation_id == Variation.id)
                 .join(ConstantSet, Assignment.constant_set_id == ConstantSet.id)
                 .where(ConstantSet.type_table_id == table.id).order_by(Variation.name))
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
        matching_authors = select(User.id).where(User.name.like("%{0}%".format(query.search)))
        condition = or_(LogRecord.description.like("%{0}%".format(query.search)), LogRecord.author_id.in_(matching_authors))
        statement = statement.where(condition)
        count_statement = count_statement.where(condition)
    return run_page(session, statement, query, LOG_SORTS, LogRecord.id,
                    lambda row: LogRow(row[0], row[1], row[2], row[3] or "", row[4] or "", row[5] or ""), count_statement)


# --------------------------------------------------------------------------- variations

VARIATION_SORTS = {"id": Variation.id, "name": Variation.name, "created": Variation.created}


def list_variations(session, query):
    """A page of variations with their parent's name; search matches name and comment."""
    parent = aliased(Variation)
    statement = (select(Variation.id, Variation.name, Variation.created, Variation.comment, parent.name, User.name)
                 .join(parent, Variation.parent_id == parent.id, isouter=True)
                 .join(User, Variation.author_id == User.id, isouter=True))
    if query.search:
        statement = statement.where(contains_text([Variation.name, Variation.comment], query.search))
    return run_page(session, statement, query, VARIATION_SORTS, Variation.id,
                    lambda row: VariationRow(row[0], row[1], row[2], row[3] or "", row[4] or "", row[5] or ""))


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
