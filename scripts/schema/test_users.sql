-- Users of the CCDB MySQL tests, the same on both servers.
-- ccdb_user: full rights on every ccdb_test* database, no password (as in CI).
-- ccdb_reader: SELECT only, for the tests that prove a dry run writes nothing.
CREATE USER IF NOT EXISTS 'ccdb_user'@'%';
GRANT ALL PRIVILEGES ON `ccdb\_test%`.* TO 'ccdb_user'@'%';
CREATE USER IF NOT EXISTS 'ccdb_reader'@'%';
GRANT SELECT ON `ccdb\_test%`.* TO 'ccdb_reader'@'%';
FLUSH PRIVILEGES;
