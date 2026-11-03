# HTTP API

The HTTP API serves the constants of a CCDB database to jobs, scripts and agents that have no database access: a
read-only web service with an [OpenAPI](https://www.openapis.org/) document, cacheable answers, the data of an
assignment in three forms, and the constants of a run as one SQLite file. Every endpoint only reads.

## Run the API

Install the `api` extra and start a server on a database:

```bash
pip install 'ccdb[api]'
ccdb -c mysql://ccdb_user@hallddb.jlab.org/ccdb api -p 8000
```

- `http://localhost:8000/api/v1/openapi.json` is the OpenAPI document; `http://localhost:8000/api/v1/docs` is a page
  where you can try every endpoint.
- `--host 0.0.0.0` listens on every interface; the default is `127.0.0.1`.

For a deployment, run the container image behind the cache (below), or any ASGI server on `ccdb.api:app` with
`CCDB_CONNECTION` set:

```bash
CCDB_CONNECTION=mysql://ccdb_user@hallddb.jlab.org/ccdb uvicorn ccdb.api:app --workers 4
```

## Endpoints

Every path starts with `/api/v1`. Times in answers are UTC instants with microseconds,
`2026-03-01T12:00:00.123456Z` ([Time](concepts/time.md)). A list hides deprecated directories, tables and
variations unless you add `deprecated=all` ([Deprecation](concepts/deprecation.md)).

| path | answers |
|---|---|
| `/health` | `{"status": "ok", "database": "ok", "version": ...}`, or 503 when the database does not answer |
| `/instance` | the CCDB version, the schema version, the instance properties |
| `/directories`, `/directories/{path}` | every directory; one directory with its subdirectories and tables |
| `/tables?search=gain*` | the tables whose name matches a pattern with `*` and `?` |
| `/tables/{path}` | one table: columns with types, units and comments, properties, variations with data, the assignment count and the newest assignment |
| `/tables/{path}/versions` | a page of the table's assignments, as `ccdb vers`: `page`, `per_page` (25, 50, 100, 200), `sort` (`created`, `run_min`, `run_max`, `variation`, `author`, `id`), `order`, `variation`, `run`, `run_min`, `run_max` |
| `/tables/{path}/schema` | a [JSON Schema](https://json-schema.org/) of the `rows` of the table's `data.json` |
| `/variations`, `/variations/{name}` | every variation; one variation with its ancestry |
| `/run-ranges` | every run range |
| `/tags`, `/tags/{name}` | every tag; one tag ([Tags](concepts/tags.md)) |
| `/logs?search=gains`, `/logs/{id}` | a page of the change log; one record |
| `/assignments/{id}` | one assignment: request string, table, variation, run range, time, author, comment, `sha256`, `size`, columns, how many assignments share its data |
| `/assignments?request=R` | the assignment a request string names |
| `/assignments/{id}/data`, `/data.json`, `/data.txt` | the data of an assignment, in three forms (below) |
| `/assignments/data.json?request=R` (and `data`, `data.txt`) | the data of the assignment a request string names |
| `/compare?a=A&b=B`, `/compare.diff?a=A&b=B` | two assignments of one table cell by cell, or as a unified diff; `A` and `B` are ids or request strings |
| `/bundle?run=R&variation=V&time=T`, `/bundle?run=R&tag=NAME` | the constants of one run as a SQLite file (below) |

A table path keeps its slashes: `/api/v1/tables/calorimeter/gains/versions`. A request string goes into the query
string URL-encoded: `/api/v1/assignments?request=%2Fcalorimeter%2Fgains%3A1000%3Adefault%3A2026-03-01`.

Errors are JSON, `{"status": 404, "error": "No table '/calorimeter/gain'"}`: 404 for an object that does not exist,
400 for a malformed parameter or request string.

## Data forms

| form | content | use |
|---|---|---|
| `data` | the stored data text: the cells of every row in order, separated by `\|`; a `\|` inside a cell is stored as `&delimiter;` | the fastest form, the bytes CCDB stores |
| `data.json` | `{"id", "request", "table", "variation", "run_min", "run_max", "created", "author", "comment", "columns", "rows"}`, rows as lists of strings | the same bytes as the web GUI's `data.json` |
| `data.txt` | the `ccdb dump` text: comment lines with the request and the comment, then one row per line | a file for `ccdb add` or a human |

Every data form carries `X-CCDB-SHA256` and `X-CCDB-Size`, the SHA-256 and the size in bytes of the stored data text
([Constant sets and their hashes](concepts/constant-sets.md)), and the SHA-256 as its `ETag`. `data` adds the shape:
`X-CCDB-Rows`, `X-CCDB-Columns`, and `X-CCDB-Schema`, a JSON list of the columns with name, type and units.
`sha256sum` of a downloaded `data` file equals `X-CCDB-SHA256`.

## Caching

Answers say how long a cache may keep them:

| address | `Cache-Control` |
|---|---|
| an assignment by id, or by a request string with a past time or a tag; a run bundle with its time or tag | `public, max-age=31536000, immutable` |
| a request string without a time or a tag | a `302` to the id form, `public, max-age=60` |
| lists, pages, table and directory info | `public, max-age=60` |
| `/health` | `no-store` |

An assignment never changes after it is added, so a URL that names one assignment may be cached for a year, and
the resolving forms redirect there, so a cache holds each assignment once however many request strings lead to it.
Every answer has an `ETag`; a request with `If-None-Match` and the current ETag gets `304` without a body.

A tag is never changed, so an answer by tag is cached for a year too. Do not reuse the name of a removed tag
(`ccdb tag rm`) for another moment: caches would keep serving the old tag's constants under that name.

Put a cache in front of the API. `docker/nginx/ccdb-api.conf` is the configuration the container image is tested
with: it keeps what the API allows, and with `proxy_cache_lock` the first request for a missing entry fetches it
while every other request for that URL waits, so a thousand jobs that start together reach the API once per URL.

## Run bundles

`/bundle` serves the constants one job needs as a SQLite file that the CCDB Python and C++ libraries open like any
CCDB database (`sqlite:///bundle.sqlite`):

- `?run=1000&variation=mc&time=2026-03-01T12:00:00`: for run 1000, the constants of `mc`, with the fallback to its
  parent variations, created at or before that UTC time;
- `?run=1000&tag=pass1`: the constants of the tag, with the tag itself, so requests with `@pass1` work in the file.

Without a time or a tag, or with a time in the future, the answer is a `302` to the explicit form at the creation
time of the newest assignment, so a bundle URL always names one set of constants. The file is built on the first
request and kept in `CCDB_API_CACHE_DIR` (in the container `/var/cache/ccdb`); its `ETag` and `X-CCDB-SHA256` are
the SHA-256 of the file. The bundle time is UTC, read with the [time format](concepts/time.md) of requests.

The file holds every directory and table, the requested variation and its parents, and, for each table, the
assignments that answer some request for that run; run ranges are clipped to the run. A request for another run
or another variation finds nothing in it.

The C++ library does this itself for an `http://` or `https://` connection string: it downloads the bundle of
the job's run, checks the SHA-256 and keeps it in a local cache ([C++ API](apis/cpp.md#http-api)).

## Container

`docker/api/Dockerfile` builds the image; it runs uvicorn with four workers on port 8000, in UTC:

```bash
docker build -f docker/api/Dockerfile -t ccdb-api .
docker run --rm -p 8000:8000 -e CCDB_CONNECTION=mysql://ccdb_user@hallddb.jlab.org/ccdb ccdb-api
```

`CCDB_API_WORKERS` and `CCDB_API_PORT` change the worker count and the port. The image checks its own health on
`/api/v1/health`.
