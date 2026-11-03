"""Responses of the HTTP API with their cache rules (docs/apis/http.md).

Three lifetimes:
- IMMUTABLE: a URL that names one assignment for good — by id, or by a request string with a past time or a tag.
  Assignments are never changed, so a cache may keep the answer for a year.
- SHORT: lists and resolving requests, which change when someone adds data; a minute.
- NO_STORE: the health check.

Every response carries an ETag: the stored sha256 of the data for the data forms, otherwise the SHA-256 of the body.
A request whose If-None-Match names the current ETag gets 304 and no body.
"""
import hashlib
import json

from fastapi.responses import RedirectResponse, Response

IMMUTABLE = "public, max-age=31536000, immutable"
SHORT = "public, max-age=60"
NO_STORE = "no-store"

JSON = "application/json; charset=utf-8"
TEXT = "text/plain; charset=utf-8"


def dump_json(value):
    """The JSON text of the API: UTF-8, keys sorted, as the web GUI writes its data.json"""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=1)


def respond(request, body, media_type, cache, etag=None, headers=None, status_code=200):
    """A response with the cache header and an ETag; 304 when the client already holds this ETag"""
    if isinstance(body, str):
        body = body.encode("utf-8")
    tag = '"{0}"'.format(etag or hashlib.sha256(body).hexdigest())
    all_headers = {"Cache-Control": cache, "ETag": tag}
    all_headers.update(headers or {})
    if status_code == 200 and tag in [each.strip() for each in request.headers.get("if-none-match", "").split(",")]:
        return Response(status_code=304, headers=all_headers)
    return Response(content=body, status_code=status_code, media_type=media_type, headers=all_headers)


def respond_json(request, value, cache=SHORT, etag=None, headers=None):
    """`value` (a pydantic model, or plain data) as JSON"""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return respond(request, dump_json(value), JSON, cache, etag, headers)


def redirect(url):
    """A resolving request answers with the address that names its result for good, cached for a minute"""
    return RedirectResponse(url, status_code=302, headers={"Cache-Control": SHORT})
