# mysql2sqlite

- https://github.com/techouse/mysql-to-sqlite3
- https://pypi.org/project/mysql-to-sqlite3/

```bash
python3 -m pip install --user --upgrade mysql-to-sqlite3
```

```bash
mysql2sqlite -d ccdb_test -u ccdb_user -h localhost -f ccdb.sqlite
```

More flags

```
sage: mysql2sqlite [OPTIONS]

  Transfer MySQL to SQLite using the provided CLI options.

Options:
  -f, --sqlite-file PATH          SQLite3 database file  [required]
  -d, --mysql-database TEXT       MySQL database name  [required]
  -u, --mysql-user TEXT           MySQL user  [required]
  -p, --prompt-mysql-password     Prompt for MySQL password
  --mysql-password TEXT           MySQL password
  -h, --mysql-host TEXT           MySQL host. Defaults to localhost.
  -P, --mysql-port INTEGER        MySQL port. Defaults to 3306.
```