# Utilities and helpful scripts

## Creating a SQLite database

There is a script to create a SQLite database from MySQL:
[scripts/mysql2sqlite/mysql2sqlite.sh](https://github.com/JeffersonLab/ccdb/blob/v2-main/scripts/mysql2sqlite/mysql2sqlite.sh).

It accepts the same arguments as `mysqldump`. The common use (in terms of CCDB):

```bash
./mysql2sqlite.sh -u <user> -h <host> <dbname> | sqlite3 database.sqlite
```

So if you have the CCDB connection string:

```
mysql://ccdb_user@mysqlhost/ccdb
```

you run the script as:

```bash
./mysql2sqlite.sh -u ccdb_user -h mysqlhost ccdb | sqlite3 database.sqlite
```

Don't forget the `-p` flag if a password is used for the CCDB MySQL DB.

> See also [Development → Convert MySQL to SQLite](development/development.md#convert-mysql-to-sqlite)
> for an alternative approach and notes on time-zone handling.
