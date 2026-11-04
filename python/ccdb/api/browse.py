"""Browse endpoints of the HTTP API: instance, directories, tables, variations, run ranges, tags, versions, logs.

Every list hides deprecated directories, tables and variations unless `deprecated=all` (docs/concepts/deprecation.md);
an object named directly is always answered, with its deprecation fields. These answers change when someone adds
data, so they are cached for a minute. The values come from ccdb.api.service, which the MCP server shares.

Route order matters: `/tables/{path}/versions` and `/tables/{path}/schema` come before `/tables/{path}`, whose path
parameter would take the suffix too.
"""
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request

from . import models, service
from .dependencies import provider_dependency
from .responses import HOURLY, SHORT, respond, respond_json

router = APIRouter()

DEPRECATED_QUERY = Query(None, description="`all` lists deprecated directories, tables and variations too")


def as_json(items):
    return [each.model_dump(mode="json") for each in items]


@router.get("/instance", response_model=models.Instance, summary="The CCDB version, the schema version and the instance properties")
def instance(request: Request, db=Depends(provider_dependency)):
    return respond_json(request, service.instance(db))


@router.get("/properties/vocabulary", summary="The standard property names per owner type, their meanings and the "
                                            "names the instance adds (property_names), as `ccdb prop` checks them")
def property_vocabulary(request: Request, db=Depends(provider_dependency)):
    return respond_json(request, service.property_vocabulary(db))


@router.get("/readiness", summary="The readiness profile: counts of units, descriptions, comments, run ranges, authors, "
                                  "stale and empty tables, shared sets and instance properties, as `ccdb db readiness --json`")
def readiness(request: Request, stale_years: int = Query(5, ge=0, le=100, description="A table is stale when no version "
                                                         "of it was created in the last N years"),
              db=Depends(provider_dependency)):
    return respond_json(request, service.readiness(db, stale_years), cache=HOURLY)


@router.get("/directories", response_model=List[models.DirectorySummary], summary="Every directory, by path")
def directories(request: Request, deprecated: Optional[str] = DEPRECATED_QUERY, db=Depends(provider_dependency)):
    return respond_json(request, as_json(service.directories(db, service.include_deprecated(deprecated))))


@router.get("/directories/{path:path}", response_model=models.DirectoryInfo, summary="One directory with its subdirectories and tables")
def directory(path: str, request: Request, deprecated: Optional[str] = DEPRECATED_QUERY, db=Depends(provider_dependency)):
    return respond_json(request, service.directory(db, path, service.include_deprecated(deprecated)))


@router.get("/tables", response_model=List[models.TableSummary], summary="Tables whose name matches a pattern (* and ?)")
def tables(request: Request, search: str = Query("*", description="Name pattern with * and ?, as `ccdb ls`"),
           deprecated: Optional[str] = DEPRECATED_QUERY, db=Depends(provider_dependency)):
    return respond_json(request, as_json(service.tables(db, search, service.include_deprecated(deprecated))))


@router.get("/tables/{path:path}/versions", response_model=models.AssignmentPage,
            summary="A page of a table's assignments, newest first by default, as `ccdb vers`")
def versions(path: str, request: Request,
             page: int = Query(1, ge=1), per_page: int = Query(50, description="25, 50, 100 or 200"),
             sort: str = Query("created", description="created, run_min, run_max, variation, author or id"), order: str = Query("desc"),
             variation: Optional[str] = None, run: Optional[int] = Query(None, ge=0), run_min: Optional[int] = Query(None, ge=0),
             run_max: Optional[int] = Query(None, ge=0), deprecated: Optional[str] = DEPRECATED_QUERY, db=Depends(provider_dependency)):
    return respond_json(request, service.versions(db, path, request.query_params, variation, run, run_min, run_max,
                                                  service.include_deprecated(deprecated)))


@router.get("/tables/{path:path}/schema", summary="A JSON Schema of the `rows` of the table's data.json")
def table_schema(path: str, request: Request, db=Depends(provider_dependency)):
    return respond_json(request, service.table_schema(db, path, request.url.path))


@router.get("/tables/{path:path}/card", response_model=models.TableCard,
            summary="A data card: description, columns with units, versions and run coverage, authors, tags, license and citation")
def table_card(path: str, request: Request, db=Depends(provider_dependency)):
    return respond_json(request, service.table_card(db, path))


@router.get("/tables/{path:path}", response_model=models.TableInfo, summary="One table: columns with units, properties, activity")
def table(path: str, request: Request, db=Depends(provider_dependency)):
    return respond_json(request, service.table(db, path))


@router.get("/variations", response_model=List[models.Variation], summary="Every variation, by name")
def variations(request: Request, deprecated: Optional[str] = DEPRECATED_QUERY, db=Depends(provider_dependency)):
    return respond_json(request, as_json(service.variations(db, service.include_deprecated(deprecated))))


@router.get("/variations/{name}", response_model=models.Variation, summary="One variation with its ancestry")
def variation(name: str, request: Request, db=Depends(provider_dependency)):
    return respond_json(request, service.variation(db, name))


@router.get("/run-ranges", response_model=List[models.RunRange], summary="Every run range")
def run_ranges(request: Request, db=Depends(provider_dependency)):
    return respond_json(request, as_json(service.run_ranges(db)))


@router.get("/tags", response_model=List[models.Tag], summary="Every tag, by name")
def tags(request: Request, db=Depends(provider_dependency)):
    return respond_json(request, as_json(service.tags(db)))


@router.get("/tags/{name}", response_model=models.Tag, summary="One tag")
def tag(name: str, request: Request, db=Depends(provider_dependency)):
    return respond_json(request, service.tag(db, name))


@router.get("/logs", response_model=models.LogPage, summary="A page of the change log, newest first; `search` matches description and author")
def logs(request: Request, page: int = Query(1, ge=1), per_page: int = Query(50), search: str = "",
         sort: str = Query("id", description="created, action, author or id"), order: str = Query("desc"), db=Depends(provider_dependency)):
    return respond_json(request, service.logs(db, request.query_params))


@router.get("/logs.atom", summary="The newest log records as an Atom feed; `search` and `per_page` as for /logs",
            responses={200: {"content": {"application/atom+xml": {}}, "description": "An Atom 1.0 feed (RFC 4287)"}})
def logs_atom(request: Request, per_page: int = Query(50), search: str = "", db=Depends(provider_dependency)):
    feed = service.logs_atom(db, request.query_params, request.url.path + ("?" + request.url.query if request.url.query else ""),
                             lambda log_id: request.url_for("log_record", log_id=log_id).path)
    return respond(request, feed, "application/atom+xml; charset=utf-8", SHORT)


@router.get("/logs/{log_id}", response_model=models.LogRecord, summary="One log record in full")
def log_record(log_id: int, request: Request, db=Depends(provider_dependency)):
    return respond_json(request, service.log_record(db, log_id))
