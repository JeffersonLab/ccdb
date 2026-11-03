"""The run bundle endpoint of the HTTP API: a SQLite file with the constants of one run, for a job to download.

    GET /api/v1/bundle?run=1000&variation=default&time=2026-03-01T12:00:00.000000
    GET /api/v1/bundle?run=1000&tag=pass1

The file is the shallow copy of that run (ccdb.snapshot.run_bundle): the variation with its parents, the constants
created at or before the time, or those of the tag with the tag's row. It is made on the first request into the cache
directory (CCDB_API_CACHE_DIR, default a directory under the system temporary directory) and served from there.
Without a time or a tag, or with a time in the future, the answer is a 302 to the explicit form at the creation time
of the newest assignment, so every bundle URL names one set of constants and may be cached for a year.
"""
import datetime
import hashlib
import os
import tempfile
import threading
from typing import Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy import func, select

from ccdb import snapshot
from ccdb.model import Assignment
from ccdb.path_utils import local_to_utc, parse_time

from .dependencies import provider_dependency
from .responses import IMMUTABLE, redirect

router = APIRouter()

BUNDLE_MEDIA_TYPE = "application/vnd.sqlite3"
_file_hashes = {}

# Builds at a time in this process (CCDB_API_BUNDLE_BUILDS): a build opens connections of its own and holds the run's
# constants while it writes them, so a burst of requests for many runs must not start them all at once (F30)
BUNDLE_BUILDS = int(os.environ.get("CCDB_API_BUNDLE_BUILDS", "4"))
_builds = threading.BoundedSemaphore(BUNDLE_BUILDS)


def cache_dir():
    return os.environ.get("CCDB_API_CACHE_DIR") or os.path.join(tempfile.gettempdir(), "ccdb_api_cache")


def file_sha256(path):
    """The SHA-256 of a bundle file, computed once per file and process"""
    if path not in _file_hashes:
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                digest.update(block)
        _file_hashes[path] = digest.hexdigest()
    return _file_hashes[path]


def build_bundle(source, run, variation="default", max_time_utc=None, tag=None):
    """The bundle's file: made now when the cache lacks it, at most BUNDLE_BUILDS at a time; a cached one needs no slot"""
    path = os.path.join(cache_dir(), snapshot.bundle_file_name(run, variation, max_time_utc, tag))
    if os.path.exists(path):
        return path
    with _builds:
        return snapshot.run_bundle(source, cache_dir(), run, variation, max_time_utc, tag)


def time_text(utc_naive):
    """A UTC instant in the request time format, which the API reads back as UTC (`Z` is not a digit, so it ends it)"""
    return utc_naive.strftime("%Y-%m-%dT%H:%M:%S.%f")


@router.get("/bundle", summary="A SQLite file with the constants of one run, by variation and time or by tag",
            responses={200: {"content": {BUNDLE_MEDIA_TYPE: {}}, "description": "The SQLite file"},
                       302: {"description": "No time, or a future one: the explicit form at the newest creation time"}})
def bundle(request: Request, run: int = Query(..., ge=0), variation: Optional[str] = Query(None),
           time: Optional[str] = Query(None, description="UTC, YYYY-MM-DDThh:mm:ss.ffffff or a leading part of it"),
           tag: Optional[str] = Query(None), db=Depends(provider_dependency)):
    if tag and (variation or time):
        raise ValueError("A bundle by tag can have neither a variation nor a time")
    if tag:
        db.get_tag(tag)                                                         # unknown → 404
        arguments = dict(tag=tag)
    else:
        variation = variation or "default"
        db.get_variation(variation)                                             # unknown → 404
        # The API's bundle times are UTC: the wall time of a server zone would make the URL depend on the server
        moment = parse_time(time).replace(tzinfo=datetime.timezone.utc) if time else None
        if moment is None or moment > datetime.datetime.now(datetime.timezone.utc):
            newest = db.session.execute(select(func.max(Assignment.created))).scalar()
            newest_utc = local_to_utc(newest).replace(tzinfo=None) if newest else datetime.datetime(1970, 1, 1)
            target = request.url_for("bundle").include_query_params(run=run, variation=variation, time=time_text(newest_utc))
            return redirect(str(target))
        arguments = dict(variation=variation, max_time_utc=moment.replace(tzinfo=None))
    # A build takes seconds and opens connections of its own: the request's connection goes back to the pool first,
    # or a burst of requests for many runs exhausts the pool while the builds run (F30)
    db.session.rollback()
    path = build_bundle(request.app.state.database.connection_string, run, **arguments)
    sha256 = file_sha256(path)
    tag_header = '"{0}"'.format(sha256)
    headers = {"Cache-Control": IMMUTABLE, "ETag": tag_header, "X-CCDB-SHA256": sha256}
    if tag_header in [each.strip() for each in request.headers.get("if-none-match", "").split(",")]:
        return Response(status_code=304, headers=headers)
    return FileResponse(path, media_type=BUNDLE_MEDIA_TYPE, filename=os.path.basename(path), headers=headers)
