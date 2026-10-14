# Deploying the web GUI

The CCDB web GUI is a read-only Flask application inside the `ccdb` package. It runs in two ways:

- **On your machine**: `ccdb gui [-p PORT]` starts Flask's development server with the CLI's connection string. Use this for yourself; it serves one request at a time and does not compress responses.
- **On a server**: a WSGI server runs `ccdbweb:app` behind a reverse proxy. CCDB ships no WSGI server; the deployment picks one. The Docker image in `docker/webgui/` uses gunicorn.

## Configuration

Everything comes from environment variables.

| variable | meaning |
|---|---|
| `CCDB_CONNECTION` | database connection string, the same variable the `ccdb` command reads, for example `mysql://ccdb_user@hallddb.jlab.org/ccdb` or `sqlite:////data/ccdb.sqlite` |
| `CCDB_WEBGUI_PROXY_FIX` | `1` when a reverse proxy in front of the app sets `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Forwarded-Host` and `X-Forwarded-Prefix`; the app then builds links with the public scheme, host and sub-path. Leave unset when clients reach the app directly, so that forged headers are ignored |
| `CCDB_WEBGUI_WORKERS` | gunicorn worker count in the Docker image (default 4) |
| `CCDB_WEBGUI_PORT` | port inside the Docker image (default 5000) |

Without a connection string the application stops at import with the message `CCDB web GUI has no database connection string...`, so a misconfigured server fails at startup instead of answering errors.

Use a **read-only database user**. The GUI never writes, and a read-only account keeps a bug in the GUI or a leaked connection string from touching the constants:

```sql
CREATE USER 'ccdb_web'@'%' IDENTIFIED BY '...';
GRANT SELECT ON ccdb.* TO 'ccdb_web'@'%';
```

## Health check

`GET /health` answers `200 {"status": "ok", "database": "ok", "version": "2.4.0"}` after a `SELECT 1` on the database, or `503 {"status": "error", ...}` when the database is unreachable. The response is never cached. Load balancers, Docker's `HEALTHCHECK` and monitoring use it.

## Docker image

Build from the repository root, so the image can build the package from `python/`:

```bash
docker build -f docker/webgui/Dockerfile -t ccdb-webgui .
docker run --rm -p 5000:5000 -e CCDB_CONNECTION=mysql://ccdb_web:...@hallddb.jlab.org/ccdb ccdb-webgui
curl http://127.0.0.1:5000/health
```

The image is `python:3.13-slim` with the `ccdb` wheel, its `web` extra (Flask) and gunicorn, running as the unprivileged user `ccdb`, with a `HEALTHCHECK` on `/health`. gunicorn starts with `--workers $CCDB_WEBGUI_WORKERS`, access and error logs on stdout, and no `--preload`: the database engine is created in each worker after the fork, which is what SQLAlchemy's connection pool expects.

`docker/docker-compose.yml` wires the image to a MySQL service with test data; it passes `CCDB_CONNECTION`, `CCDB_WEBGUI_WORKERS` and `CCDB_WEBGUI_PROXY_FIX`.

## Any other WSGI server

Install the package with its web extra and the server of your choice, keep `ccdbweb.py` (the WSGI entry point, from `python/ccdbweb.py`) in the working directory, and start the server there:

```bash
pip install "ccdb[web]" gunicorn
cp python/ccdbweb.py /srv/ccdb-webgui/
cd /srv/ccdb-webgui
CCDB_CONNECTION=mysql://ccdb_web:...@hallddb.jlab.org/ccdb gunicorn --workers 4 --bind 127.0.0.1:5000 --access-logfile - ccdbweb:app
```

Start the server from a directory that does not contain a `ccdb` source checkout: Python imports `ccdb` from the current directory first, and the checkout would shadow the installed package.

## Reverse proxy, sub-path and compression

The app works under a sub-path. The proxy forwards the prefix and the app, with `CCDB_WEBGUI_PROXY_FIX=1`, builds every link under it. Enable compression at the proxy: the pages gzip to a few kilobytes (the full table tree of 1000 tables is 14 KB compressed and 400 KB raw), and the Bootstrap stylesheet goes from 226 KB to 30 KB. The application itself does not compress.

nginx example, serving the GUI under `/ccdb/`:

```nginx
location /ccdb/ {
    proxy_pass http://127.0.0.1:5000/;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header X-Forwarded-Host $host;
    proxy_set_header X-Forwarded-Prefix /ccdb;
}
gzip on;
gzip_types text/css application/javascript application/json text/plain image/svg+xml;  # text/html is always included
gzip_min_length 1024;
```

Static files under `/ccdb/static/` may be cached for a long time; they change only with a CCDB release. Assignment data (`/assignments/<id>/data.json` and `data.txt`, or a request string with a timestamp) already carries `Cache-Control: public, max-age=86400`.

## Logging

The app logs through Python's `logging` under the name `ccdb.webgui`: one line when the database engine is created, and the usual request errors. gunicorn's `--access-logfile -` and `--error-logfile -` put request and server logs on stdout, where Docker and systemd collect them.

## Building the wheel

```bash
rm -rf build
uv build --wheel
```

Remove `build/` first: setuptools reuses files from an earlier build in that directory, and a wheel built over a stale `build/` ships files that no longer exist in the source tree. The wheel carries the web GUI's templates and static files, including the vendored Bootstrap 5.3.8 and its license (`python -m ccdb.webgui.vendor` verifies them against a sha256 manifest).
