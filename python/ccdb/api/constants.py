"""Assignment endpoints of the HTTP API: one assignment by id, request string or tag, its data in three forms, and the
comparison of two assignments (docs/apis/http.md).

Addresses and caching:
- `/assignments/{id}/…` names one assignment for good: cached for a year.
- `/assignments/…?request=R` with a past time or a tag in R names one assignment too: answered directly, cached for a year.
- `/assignments/…?request=R` without a time or a tag resolves to the newest assignment: a 302 to the id form, cached for
  a minute, so caches keep each assignment once however many requests lead to it.

The data forms: `data` is the stored data text (cells separated by `|`, rows by `|` too, the shape in the headers),
`data.json` is byte-identical to the web GUI's, `data.txt` is the `ccdb dump` text. Every data form carries the stored
SHA-256 and size of the data text in `X-CCDB-SHA256` and `X-CCDB-Size`, and the SHA-256 as its ETag.
"""
import json
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request

from . import models, service
from .dependencies import provider_dependency
from .responses import IMMUTABLE, JSON, SHORT, TEXT, dump_json, redirect, respond

router = APIRouter()

REQUEST_QUERY = Query(None, alias="request", description="A CCDB request string: /path:run:variation:time or /path:run@tag")
DATA_FORMS = ("data", "data.json", "data.txt")
DATA_RESPONSES = {200: {"description": "`data`: the stored data text; `data.json`: the web GUI's JSON; `data.txt`: the `ccdb dump` text",
                        "content": {TEXT: {}, JSON: {}}}}
REDIRECT_RESPONSE = {302: {"description": "The request resolves to the newest assignment: its id form"}}


def data_headers(assignment):
    return {"X-CCDB-SHA256": assignment.constant_set.sha256, "X-CCDB-Size": str(assignment.constant_set.size)}


def answer_data(request, assignment, form):
    """One data form of an assignment, with the stored hash as ETag"""
    if form not in DATA_FORMS:
        raise LookupError("No assignment form '{0}'; the forms are {1}".format(form, ", ".join(DATA_FORMS)))
    table = assignment.constant_set.type_table
    sha256 = assignment.constant_set.sha256
    if form == "data":
        schema = json.dumps([column.model_dump(exclude_none=True) for column in service.columns_of(table)], ensure_ascii=True)
        headers = dict(data_headers(assignment), **{"X-CCDB-Rows": str(table.rows_count), "X-CCDB-Columns": str(table.columns_count),
                                                    "X-CCDB-Schema": schema})
        return respond(request, assignment.constant_set.vault, TEXT, IMMUTABLE, sha256, headers)
    if form == "data.json":
        return respond(request, service.data_json(assignment), JSON, IMMUTABLE, sha256, data_headers(assignment))
    return respond(request, service.data_text(assignment), TEXT, IMMUTABLE, sha256, data_headers(assignment))


def id_url(request, assignment_id, form=None):
    if form:
        return str(request.url_for("assignment_data_by_id", assignment_id=assignment_id, form=form))
    return str(request.url_for("assignment_by_id", assignment_id=assignment_id))


@router.get("/assignments", response_model=models.Assignment, responses=REDIRECT_RESPONSE,
            summary="The assignment a request string names; without a time or a tag, a 302 to the id form")
def assignment_by_request(request: Request, request_string: Optional[str] = REQUEST_QUERY, db=Depends(provider_dependency)):
    found, for_good = service.resolve(db, request_string=request_string)
    if not for_good:
        return redirect(id_url(request, found.id))
    return respond(request, dump_json(service.assignment(db, found).model_dump(mode="json")), JSON, IMMUTABLE)


@router.get("/assignments/{assignment_id:int}", response_model=models.Assignment, summary="One assignment by its database id")
def assignment_by_id(assignment_id: int, request: Request, db=Depends(provider_dependency)):
    found, _ = service.resolve(db, assignment_id=assignment_id)
    return respond(request, dump_json(service.assignment(db, found).model_dump(mode="json")), JSON, IMMUTABLE)


@router.get("/assignments/{form}", summary="A data form (data, data.json, data.txt) of the assignment a request string names",
            responses={**DATA_RESPONSES, **REDIRECT_RESPONSE})
def assignment_data_by_request(form: str, request: Request, request_string: Optional[str] = REQUEST_QUERY, db=Depends(provider_dependency)):
    if form not in DATA_FORMS:
        raise LookupError("No assignment form '{0}'; the forms are {1}".format(form, ", ".join(DATA_FORMS)))
    found, for_good = service.resolve(db, request_string=request_string)
    if not for_good:
        return redirect(id_url(request, found.id, form))
    return answer_data(request, found, form)


@router.get("/assignments/{assignment_id:int}/{form}", summary="A data form (data, data.json, data.txt) of an assignment by its database id",
            responses=DATA_RESPONSES)
def assignment_data_by_id(assignment_id: int, form: str, request: Request, db=Depends(provider_dependency)):
    if form not in DATA_FORMS:
        raise LookupError("No assignment form '{0}'; the forms are {1}".format(form, ", ".join(DATA_FORMS)))
    found, _ = service.resolve(db, assignment_id=assignment_id)
    return answer_data(request, found, form)


@router.get("/compare", summary="Two assignments of one table cell by cell, as the web GUI's compare/data.json")
def compare(request: Request, a: str = Query(..., description="Request string or database id"),
            b: str = Query(..., description="Request string or database id"),
            changed: int = Query(0, ge=0, le=1, description="1 keeps only the rows with a change"), db=Depends(provider_dependency)):
    side_a, side_b, for_good = service.compare_pair(db, a, b)
    body = json.dumps(service.compare(side_a, side_b, bool(changed)), ensure_ascii=False, sort_keys=True, indent=1)
    return respond(request, body, JSON, IMMUTABLE if for_good else SHORT)


@router.get("/compare.diff", summary="Two assignments of one table as a unified diff (`diff -u`) of their `data.txt` rows")
def compare_diff(request: Request, a: str = Query(...), b: str = Query(...), db=Depends(provider_dependency)):
    side_a, side_b, for_good = service.compare_pair(db, a, b)
    return respond(request, service.compare_diff(side_a, side_b), TEXT, IMMUTABLE if for_good else SHORT)
