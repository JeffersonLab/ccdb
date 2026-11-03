"""The JSON shapes of the HTTP API, as pydantic models; they make the OpenAPI document (/api/v1/openapi.json).

Times are UTC instants in ISO 8601 with microseconds, `2026-03-01T12:00:00.123456Z` (docs/concepts/time.md).
The data forms of an assignment (`data`, `data.json`, `data.txt`) are documented in docs/apis/http.md; data.json is
byte-identical to the web GUI's.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Health(BaseModel):
    status: str = Field(description="`ok`, or `error` with HTTP 503 when the database does not answer")
    database: str = Field(description="`ok` or `unavailable`")
    version: str = Field(description="CCDB version of the server")


class Instance(BaseModel):
    version: str = Field(description="CCDB version of the server")
    schema_version: int
    properties: Dict[str, str] = Field(description="Instance properties (`ccdb prop set --instance`): experiment, "
                                                   "description, license, citation, contact, url")


class Deprecation(BaseModel):
    deprecated: bool = False
    deprecated_time: Optional[str] = None
    deprecation_comment: Optional[str] = None


class DirectorySummary(Deprecation):
    path: str
    name: str
    comment: str


class TableSummary(Deprecation):
    path: str
    name: str
    rows: int
    column_count: int
    comment: str


class DirectoryInfo(DirectorySummary):
    created: str
    modified: str
    author: str
    properties: Dict[str, str]
    directories: List[DirectorySummary]
    tables: List[TableSummary]


class Column(BaseModel):
    name: str
    type: str = Field(description="int, uint, long, ulong, double, string or bool")
    units: Optional[str] = None
    comment: str = ""


class TableInfo(TableSummary):
    created: str
    modified: str
    author: str
    columns: List[Column] = Field(description="The columns in order")
    properties: Dict[str, str]
    variations: List[str] = Field(description="Variations with at least one assignment of the table")
    assignments: int
    last_assignment: Optional[str] = Field(None, description="Creation time of the newest assignment")
    last_author: str = ""


class CardVariation(BaseModel):
    name: str
    versions: int = Field(description="Assignments of the table in this variation")
    runs: List[List[int]] = Field(description="The runs the assignments cover, as merged [first, last] intervals")


class CardChange(BaseModel):
    created: str = Field(description="UTC")
    author: str
    variation: str
    comment: str


class TableCard(BaseModel):
    """A data card: what a reader needs to use a table's constants and to cite them"""
    path: str
    name: str
    description: str = Field(description="The table's comment")
    deprecated: bool = False
    rows: int
    columns: List[Column] = Field(description="The columns in order, with types, units and comments")
    properties: Dict[str, str] = Field(description="The table's properties (`ccdb prop`), e.g. purpose, procedure, source_url")
    versions: int = Field(description="Assignments of the table in every variation")
    variations: List[CardVariation]
    authors: List[Dict[str, Any]] = Field(description="Who added the assignments: name and count, most first")
    last_change: Optional[CardChange] = Field(None, description="The newest assignment")
    tags: List[str] = Field(description="Tags under which the table has constants")
    license: str = Field("", description="The instance property `license`")
    citation: str = Field("", description="The instance property `citation`")
    instance: Dict[str, str] = Field(description="The instance properties experiment, license, citation, contact, url")


class Variation(Deprecation):
    name: str
    comment: str
    parent: Optional[str] = Field(None, description="The variation this one inherits from; none for default")
    chain: List[str] = Field(description="The ancestry from the root: default, ..., this variation")
    created: str
    author: str


class RunRange(BaseModel):
    id: int
    name: str
    min: int
    max: int
    comment: str


class Tag(BaseModel):
    name: str
    variation: str
    time: str = Field(description="The moment the tag freezes, UTC")
    comment: str
    author: str
    created: str


class AssignmentRow(BaseModel):
    id: int
    request: str = Field(description="The request string that names this assignment, as `ccdb vers` and the web GUI give it")
    run_min: int
    run_max: int
    variation: str
    created: str
    author: str
    comment: str
    shared_by: int = Field(description="How many assignments use this assignment's data; more than 1 is shared data")


class Assignment(BaseModel):
    id: int
    request: str
    table: str
    variation: str
    run_min: int
    run_max: int
    created: str
    author: str
    comment: str
    sha256: str = Field(description="SHA-256 of the stored data text, the ETag of the data forms")
    size: int = Field(description="Bytes of the stored data text (UTF-8)")
    rows: int
    columns: List[Column]
    shared_by: int


class PageInfo(BaseModel):
    page: int
    per_page: int
    pages: int
    total: int
    sort: str
    order: str


class AssignmentPage(PageInfo):
    items: List[AssignmentRow]


class LogRow(BaseModel):
    id: int
    created: str
    action: str
    description: str
    comment: str
    author: str


class LogPage(PageInfo):
    items: List[LogRow]


class LogRecord(LogRow):
    affected: List[List] = Field(description="[kind, id] pairs the record names: assignments, variations, typeTables, "
                                             "directories, users")


class Error(BaseModel):
    status: int
    error: str
