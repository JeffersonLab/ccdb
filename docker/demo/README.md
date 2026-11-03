# CCDB demo stack

MariaDB with the ePIC-shaped demo tables (`scripts/demo/make_epic_tables.py`), the HTTP API behind its nginx cache,
and the web GUI, on one machine. From the repository root:

```bash
docker compose -f docker/demo/compose.yml up --build -d
python scripts/demo/check.py
docker compose -f docker/demo/compose.yml down -v
```

- API through the cache: http://localhost:8080/api/v1/docs
- web GUI: http://localhost:5000
- database for the JANA2 demo application: `mysql://root@127.0.0.1:3306/ccdb_demo` (no password, loopback only)

docs/get-started/demo.md describes the tables and the JANA2 application.
