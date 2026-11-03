# CCDB HTTP API image: the ccdb package with its api extra, served by uvicorn (docs/apis/http.md).
#
# Build from the repository root:
#     docker build -f docker/api/Dockerfile -t ccdb-api .
# Run against a database, behind the cache of docker/nginx/ccdb-api.conf:
#     docker run --rm -p 8000:8000 -e CCDB_CONNECTION=mysql://ccdb_user@hallddb.jlab.org/ccdb ccdb-api
#
# The container runs in UTC: the API reads and writes UTC times (docs/concepts/time.md), and a run bundle URL names
# its time in UTC. Run bundles are written to CCDB_API_CACHE_DIR; mount a volume there to keep them across restarts.

FROM python:3.13.7-slim AS build
WORKDIR /src
COPY pyproject.toml README.md ./
COPY python ./python
RUN pip install --no-cache-dir --upgrade pip build && python -m build --wheel --outdir /wheels .

FROM python:3.13.7-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=UTC \
    CCDB_API_WORKERS=4 \
    CCDB_API_PORT=8000 \
    CCDB_API_CACHE_DIR=/var/cache/ccdb
RUN useradd --create-home --uid 1000 ccdb && mkdir -p /var/cache/ccdb && chown ccdb /var/cache/ccdb
WORKDIR /app
COPY --from=build /wheels/*.whl /tmp/
RUN pip install --no-cache-dir "$(ls /tmp/ccdb-*.whl)[api]" && rm /tmp/*.whl
USER ccdb
EXPOSE 8000
VOLUME /var/cache/ccdb
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/api/v1/health' % os.environ.get('CCDB_API_PORT', '8000'), timeout=4)"
# The application is made on first access to ccdb.api:app, in each worker after the fork (ccdb/api/database.py)
CMD ["sh", "-c", "exec uvicorn ccdb.api:app --host 0.0.0.0 --port ${CCDB_API_PORT} --workers ${CCDB_API_WORKERS} --proxy-headers"]
