# CCDB web GUI image: the ccdb package with its web extra, served by gunicorn.
#
# Build from the repository root (the compose file does this):
#     docker build -f docker/webgui/Dockerfile -t ccdb-webgui .
# Run against a database:
#     docker run --rm -p 5000:5000 -e CCDB_CONNECTION=mysql://ccdb_user@hallddb.jlab.org/ccdb ccdb-webgui
#
# gunicorn is the image's choice of WSGI server; CCDB itself ships none. The reverse proxy, TLS and
# compression belong to the deployment in front of this container (see docs/deployment/webgui.md).

FROM python:3.13-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY python ./python
# A stale build/ directory makes setuptools ship deleted files; the context never contains one (.dockerignore),
# and the build runs in a fresh layer.
RUN pip install --no-cache-dir --upgrade pip build && python -m build --wheel --outdir /wheels .

FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CCDB_WEBGUI_WORKERS=4 \
    CCDB_WEBGUI_PORT=5000
RUN useradd --create-home --uid 1000 ccdb
WORKDIR /app
COPY --from=build /wheels/*.whl /tmp/
# ccdbweb.py is the WSGI entry point (gunicorn ccdbweb:app); it lives outside the package, so the image carries it.
COPY python/ccdbweb.py /app/ccdbweb.py
RUN pip install --no-cache-dir "$(ls /tmp/ccdb-*.whl)[web]" gunicorn && rm /tmp/*.whl
USER ccdb
EXPOSE 5000
# The app fails at import without CCDB_CONNECTION, so a misconfigured container stops at once.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/health' % os.environ.get('CCDB_WEBGUI_PORT', '5000'), timeout=4)"
# No --preload: the database engine is created lazily in each worker after the fork (see ccdb/webgui/db.py).
CMD ["sh", "-c", "exec gunicorn --workers ${CCDB_WEBGUI_WORKERS} --bind 0.0.0.0:${CCDB_WEBGUI_PORT} --access-logfile - --error-logfile - ccdbweb:app"]
