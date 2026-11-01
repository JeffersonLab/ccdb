# Utilities and helpful scripts

## Creating a SQLite database

To create a SQLite database from a MySQL one, dump the MySQL database and convert the dump with
[scripts/mysql2sqlite/mysql2sqlite](https://github.com/JeffersonLab/ccdb/blob/v2-main/scripts/mysql2sqlite/mysql2sqlite),
which rewrites MySQL-flavored SQL for SQLite. For the CCDB connection string
`mysql://ccdb_user@mysqlhost/ccdb`:

```bash
mysqldump --skip-tz-utc -u ccdb_user -h mysqlhost ccdb > dump.mysql.sql
./mysql2sqlite dump.mysql.sql | sqlite3 database.sqlite
```

Add `-p` to `mysqldump` when the account has a password. `--skip-tz-utc` keeps the times as MySQL
stores them.

> See also [Development → Convert MySQL to SQLite](development/development.md#convert-mysql-to-sqlite)
> for an alternative approach and notes on time-zone handling.
