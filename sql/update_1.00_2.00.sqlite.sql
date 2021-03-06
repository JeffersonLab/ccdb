ALTER TABLE variations ADD COLUMN isLocked TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE variations ADD COLUMN lockTime TIMESTAMP NULL DEFAULT NULL;
ALTER TABLE variations ADD COLUMN lockAuthorId INT(11) NULL DEFAULT NULL;
ALTER TABLE variations ADD COLUMN goBackBehavior INT(11) NOT NULL DEFAULT 0;
ALTER TABLE variations ADD COLUMN goBackTime TIMESTAMP NULL DEFAULT NULL;

ALTER TABLE typeTables ADD COLUMN isDeprecated TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE typeTables ADD COLUMN deprecatedById INT(11) NOT NULL DEFAULT -1;
ALTER TABLE typeTables ADD COLUMN isLocked TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE typeTables ADD COLUMN lockAuthorId INT(11) NULL DEFAULT NULL;
ALTER TABLE typeTables ADD COLUMN lockTime TIMESTAMP NULL DEFAULT NULL;

ALTER TABLE directories ADD COLUMN isDeprecated TINYINT(1) NOT NULL DEFAULT 0;
ALTER TABLE directories ADD COLUMN deprecatedById INT(11) NOT NULL DEFAULT -1;


CREATE TABLE IF NOT EXISTS assignmentsMaterializedView (
  id INT(11) NOT NULL,
  assignmentsId INT(11) NOT NULL,
  variationsId INT(11) NOT NULL,
  constantSetsId INT(11) NOT NULL,
  typeTablesId INT(11) NOT NULL,
  runRangesId INT(11) NOT NULL,
  runMin INT(11) NOT NULL,
  runMax INT(11) NOT NULL,
  assignmentTime TIMESTAMP NOT NULL,
  PRIMARY KEY (id ASC));

UPDATE schemaVersions SET schemaVersion = 5 WHERE id = 1;