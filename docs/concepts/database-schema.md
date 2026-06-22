# Database schema

This page documents the CCDB database tables. See [Conceptual design](conceptual-design.md) for the
reasoning behind the schema and [Concepts illustrated](concepts.md) for how these tables map to
namepaths, table types, constant sets, and assignments.

The authoritative source of the MySQL schema is the
[MySQL Workbench](https://www.mysql.com/products/workbench/) project
[ccdb_eer_diagram.mwb](https://github.com/JeffersonLab/ccdb/blob/v2-main/sql/ccdb_eer_diagram.mwb) in
the `sql/` directory.

## assignments

```
+---------------+------------------+------+-----+---------------------+----------------+
| Field         | Type             | Null | Key | Default             | Extra          |
+---------------+------------------+------+-----+---------------------+----------------+
| id            | int(10) unsigned | NO   | PRI | NULL                | auto_increment |
| created       | timestamp        | NO   | MUL | CURRENT_TIMESTAMP   |                |
| modified      | timestamp        | NO   |     | 2007-01-01 00:00:00 |                |
| variationId   | int(11)          | NO   | MUL | NULL                |                |
| runRangeId    | int(11)          | YES  | MUL | NULL                |                |
| eventRangeId  | int(11)          | YES  | MUL | NULL                |                |
| constantSetId | int(11)          | NO   | MUL | NULL                |                |
| authorId      | int(11)          | NO   |     | 1                   |                |
| comment       | text             | YES  |     | NULL                |                |
+---------------+------------------+------+-----+---------------------+----------------+
```

## columns

```
+------------+------------------------------------------------------------+------+-----+---------------------+----------------+
| Field      | Type                                                       | Null | Key | Default             | Extra          |
+------------+------------------------------------------------------------+------+-----+---------------------+----------------+
| id         | int(11)                                                    | NO   | PRI | NULL                | auto_increment |
| created    | timestamp                                                  | NO   |     | CURRENT_TIMESTAMP   |                |
| modified   | timestamp                                                  | NO   |     | 2007-01-01 00:00:00 |                |
| name       | varchar(45)                                                | NO   |     | NULL                |                |
| typeId     | int(11)                                                    | NO   | MUL | NULL                |                |
| columnType | enum('int','uint','long','ulong','double','string','bool') | YES  |     | NULL                |                |
| order      | int(11)                                                    | NO   |     | NULL                |                |
| comment    | text                                                       | YES  |     | NULL                |                |
+------------+------------------------------------------------------------+------+-----+---------------------+----------------+
```

## constantSets

```
+----------------+-----------+------+-----+---------------------+----------------+
| Field          | Type      | Null | Key | Default             | Extra          |
+----------------+-----------+------+-----+---------------------+----------------+
| id             | int(11)   | NO   | PRI | NULL                | auto_increment |
| created        | timestamp | NO   |     | CURRENT_TIMESTAMP   |                |
| modified       | timestamp | NO   |     | 2007-01-01 00:00:00 |                |
| vault          | longtext  | NO   |     | NULL                |                |
| constantTypeId | int(11)   | NO   | MUL | NULL                |                |
+----------------+-----------+------+-----+---------------------+----------------+
```

## directories

```
+----------+--------------+------+-----+---------------------+----------------+
| Field    | Type         | Null | Key | Default             | Extra          |
+----------+--------------+------+-----+---------------------+----------------+
| id       | int(11)      | NO   | PRI | NULL                | auto_increment |
| created  | timestamp    | NO   |     | CURRENT_TIMESTAMP   |                |
| modified | timestamp    | NO   |     | 2007-01-01 00:00:00 |                |
| name     | varchar(255) | NO   |     |                     |                |
| parentId | int(11)      | NO   | MUL | 0                   |                |
| authorId | int(11)      | NO   |     | 1                   |                |
| comment  | text         | YES  |     | NULL                |                |
+----------+--------------+------+-----+---------------------+----------------+
```

## eventRanges

```
+-----------+-----------+------+-----+---------------------+----------------+
| Field     | Type      | Null | Key | Default             | Extra          |
+-----------+-----------+------+-----+---------------------+----------------+
| id        | int(11)   | NO   | PRI | NULL                | auto_increment |
| created   | timestamp | NO   |     | CURRENT_TIMESTAMP   |                |
| modified  | timestamp | NO   |     | 2007-01-01 00:00:00 |                |
| runNumber | int(11)   | NO   |     | NULL                |                |
| eventMin  | int(11)   | NO   |     | NULL                |                |
| eventMax  | int(11)   | NO   |     | NULL                |                |
| comment   | text      | YES  |     | NULL                |                |
+-----------+-----------+------+-----+---------------------+----------------+
```

## logs

```
+-------------+--------------+------+-----+-------------------+----------------+
| Field       | Type         | Null | Key | Default           | Extra          |
+-------------+--------------+------+-----+-------------------+----------------+
| id          | int(11)      | NO   | PRI | NULL              | auto_increment |
| created     | timestamp    | NO   |     | CURRENT_TIMESTAMP |                |
| affectedIds | text         | NO   |     | NULL              |                |
| action      | varchar(7)   | NO   |     | NULL              |                |
| description | varchar(255) | NO   |     | NULL              |                |
| comment     | text         | YES  |     | NULL              |                |
| authorId    | int(11)      | NO   | MUL | NULL              |                |
+-------------+--------------+------+-----+-------------------+----------------+
```

## runRanges

```
+----------+-------------+------+-----+---------------------+----------------+
| Field    | Type        | Null | Key | Default             | Extra          |
+----------+-------------+------+-----+---------------------+----------------+
| id       | int(11)     | NO   | PRI | NULL                | auto_increment |
| created  | timestamp   | NO   |     | 2007-01-01 00:00:00 |                |
| modified | timestamp   | NO   |     | CURRENT_TIMESTAMP   |                |
| name     | varchar(45) | YES  |     |                     |                |
| runMin   | int(11)     | NO   | MUL | NULL                |                |
| runMax   | int(11)     | NO   |     | NULL                |                |
| comment  | text        | YES  |     | NULL                |                |
+----------+-------------+------+-----+---------------------+----------------+
```

## schemaVersions

```
+---------------+---------+------+-----+---------+-------+
| Field         | Type    | Null | Key | Default | Extra |
+---------------+---------+------+-----+---------+-------+
| id            | int(11) | NO   | PRI | NULL    |       |
| schemaVersion | int(11) | NO   |     | 1       |       |
+---------------+---------+------+-----+---------+-------+
```

## tags

```
+-------+-------------+------+-----+---------+----------------+
| Field | Type        | Null | Key | Default | Extra          |
+-------+-------------+------+-----+---------+----------------+
| id    | int(11)     | NO   | PRI | NULL    | auto_increment |
| name  | varchar(45) | NO   |     | NULL    |                |
+-------+-------------+------+-----+---------+----------------+
```

## typeTables

```
+--------------+--------------+------+-----+---------------------+----------------+
| Field        | Type         | Null | Key | Default             | Extra          |
+--------------+--------------+------+-----+---------------------+----------------+
| id           | int(11)      | NO   | PRI | NULL                | auto_increment |
| created      | timestamp    | NO   |     | CURRENT_TIMESTAMP   |                |
| modified     | timestamp    | NO   |     | 2007-01-01 00:00:00 |                |
| directoryId  | int(11)      | NO   | MUL | NULL                |                |
| name         | varchar(255) | NO   |     | NULL                |                |
| nRows        | int(11)      | NO   |     | 1                   |                |
| nColumns     | int(11)      | NO   |     | NULL                |                |
| nAssignments | int(11)      | NO   |     | 0                   |                |
| authorId     | int(11)      | NO   |     | 1                   |                |
| comment      | text         | YES  |     | NULL                |                |
+--------------+--------------+------+-----+---------------------+----------------+
```

## users

```
+----------------+--------------+------+-----+---------------------+----------------+
| Field          | Type         | Null | Key | Default             | Extra          |
+----------------+--------------+------+-----+---------------------+----------------+
| id             | int(11)      | NO   | PRI | NULL                | auto_increment |
| created        | timestamp    | NO   |     | CURRENT_TIMESTAMP   |                |
| lastActionTime | timestamp    | NO   |     | 2001-01-01 00:00:00 |                |
| name           | varchar(100) | NO   |     | NULL                |                |
| password       | varchar(100) | YES  |     | NULL                |                |
| roles          | text         | NO   |     | NULL                |                |
| info           | varchar(125) | NO   |     | NULL                |                |
| isDeleted      | tinyint(1)   | NO   |     | 0                   |                |
+----------------+--------------+------+-----+---------------------+----------------+
```

## variations

```
+-------------+--------------+------+-----+---------------------+----------------+
| Field       | Type         | Null | Key | Default             | Extra          |
+-------------+--------------+------+-----+---------------------+----------------+
| id          | int(11)      | NO   | PRI | NULL                | auto_increment |
| created     | timestamp    | NO   |     | 2007-01-01 00:00:00 |                |
| modified    | timestamp    | NO   |     | CURRENT_TIMESTAMP   |                |
| name        | varchar(100) | NO   | MUL | default             |                |
| description | varchar(255) | YES  |     | NULL                |                |
| authorId    | int(11)      | NO   |     | 1                   |                |
| comment     | text         | YES  |     | NULL                |                |
| parentId    | int(11)      | NO   | MUL | 0                   |                |
+-------------+--------------+------+-----+---------------------+----------------+
```

## variations_has_tags

```
+---------------+---------+------+-----+---------+-------+
| Field         | Type    | Null | Key | Default | Extra |
+---------------+---------+------+-----+---------+-------+
| variations_id | int(11) | NO   | PRI | NULL    |       |
| tags_id       | int(11) | NO   | PRI | NULL    |       |
+---------------+---------+------+-----+---------+-------+
```
