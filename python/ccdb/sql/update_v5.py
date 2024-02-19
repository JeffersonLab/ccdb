from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

mysql_update_v5_queries = [
    """ ALTER TABLE `variations`
        ADD COLUMN `isLocked` TINYINT NOT NULL DEFAULT 0 AFTER `parentId`,
        ADD COLUMN `lockTime` TIMESTAMP NULL DEFAULT NULL AFTER `isLocked`,
        ADD COLUMN `lockedByUserId` INT NULL DEFAULT NULL AFTER `lockTime`,
        ADD COLUMN `goBackBehavior` INT NOT NULL DEFAULT 0 AFTER `lockedByUserId`,
        ADD COLUMN `goBackTime` TIMESTAMP NULL DEFAULT NULL AFTER `goBackBehavior`,
        ADD COLUMN `isDeprecated` TINYINT NOT NULL DEFAULT 0 AFTER `goBackTime`,
        ADD COLUMN `deprecatedByUserId` INT NULL DEFAULT NULL AFTER `isDeprecated`;
    """,
    """
        ALTER TABLE `typeTables`
        ADD COLUMN `isDeprecated` TINYINT NOT NULL DEFAULT 0 AFTER `comment`,
        ADD COLUMN `deprecatedByUserId` INT NULL DEFAULT NULL AFTER `isDeprecated`,
        ADD COLUMN `isLocked` TINYINT NOT NULL DEFAULT 0 AFTER `deprecatedByUserId`,
        ADD COLUMN `lockedByUserId` INT NULL DEFAULT NULL AFTER `isLocked`,
        ADD COLUMN `lockTime` TIMESTAMP NULL DEFAULT NULL AFTER `lockedByUserId`;
    """,
    """
        ALTER TABLE `directories`
        ADD COLUMN `isDeprecated` TINYINT NOT NULL DEFAULT 0 AFTER `comment`,
        ADD COLUMN `deprecatedByUserId` INT NULL DEFAULT NULL AFTER `isDeprecated`,
        ADD COLUMN `isLocked` TINYINT NOT NULL DEFAULT 0 AFTER `deprecatedByUserId`,
        ADD COLUMN `lockedByUserId` INT NULL DEFAULT NULL AFTER `isLocked`;
    """,
    """
    CREATE TABLE IF NOT EXISTS `assignmentsMaterializedView` (
      `id` INT NOT NULL AUTO_INCREMENT,
      `assignmentsId` INT NOT NULL,
      `variationsId` INT NOT NULL,
      `constantSetsId` INT NOT NULL,
      `typeTablesId` INT NOT NULL,
      `runRangesId` INT NOT NULL,
      `runMin` INT NOT NULL,
      `runMax` INT NOT NULL,
      `assignmentTime` TIMESTAMP NOT NULL,
      PRIMARY KEY (`id`));
    
    UPDATE `schemaVersions` SET schemaVersion = 5 WHERE `id` = 1;
    """,
]

sqlite_update_v5_queries = [
    "ALTER TABLE variations ADD COLUMN isLocked TINYINT(1) NOT NULL DEFAULT 0;",
    "ALTER TABLE variations ADD COLUMN lockTime TIMESTAMP NULL DEFAULT NULL;",
    "ALTER TABLE variations ADD COLUMN lockAuthorId INT(11) NULL DEFAULT NULL;",
    "ALTER TABLE variations ADD COLUMN goBackBehavior INT(11) NOT NULL DEFAULT 0;",
    "ALTER TABLE variations ADD COLUMN goBackTime TIMESTAMP NULL DEFAULT NULL;",

    "ALTER TABLE typeTables ADD COLUMN isDeprecated TINYINT(1) NOT NULL DEFAULT 0;",
    "ALTER TABLE typeTables ADD COLUMN deprecatedById INT(11) NOT NULL DEFAULT -1;",
    "ALTER TABLE typeTables ADD COLUMN isLocked TINYINT(1) NOT NULL DEFAULT 0;",
    "ALTER TABLE typeTables ADD COLUMN lockAuthorId INT(11) NULL DEFAULT NULL;",
    "ALTER TABLE typeTables ADD COLUMN lockTime TIMESTAMP NULL DEFAULT NULL;",

    "ALTER TABLE directories ADD COLUMN isDeprecated TINYINT(1) NOT NULL DEFAULT 0;",
    "ALTER TABLE directories ADD COLUMN deprecatedById INT(11) NOT NULL DEFAULT -1;",

    """
    CREATE TABLE IF NOT EXISTS `assignmentsMaterializedView` (
        `id` INT NOT NULL AUTO_INCREMENT,
        `assignmentsId` INT NOT NULL,
        `variationsId` INT NOT NULL,
        `constantSetsId` INT NOT NULL,
        `typeTablesId` INT NOT NULL,
        `runRangesId` INT NOT NULL,
        `runMin` INT NOT NULL,
        `runMax` INT NOT NULL,
        `assignmentTime` TIMESTAMP NOT NULL,
        PRIMARY KEY (`id`))
        ENGINE = MyISAM;
        """,

    "UPDATE schemaVersions SET schemaVersion = 5 WHERE id = 1;",
]


def update_v5(connection_string, queries=None):
    """
    Execute a series of SQL update queries to migrate the database to version 5,
    after checking if the current schema version is 4.

    :param connection_string: SQLAlchemy database connection string.
    :param queries: List of SQL queries to be executed.
    """

    if not queries:
        if 'mysql' in connection_string or 'mariadb' in connection_string:
            queries = mysql_update_v5_queries
        elif 'sqlite' in connection_string:
            queries = sqlite_update_v5_queries
        else:
            raise ValueError(f"Connection string '{connection_string}' is not recognized as SQLite or MySQL/MariaDB")

    engine = create_engine(connection_string)

    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            # Check current schema version
            schema_version_result = connection.execute(
                text("SELECT schemaVersion FROM `schemaVersions` WHERE `id` = 1;"))
            schema_version = schema_version_result.scalar()

            if schema_version != 4:
                raise ValueError(f"Current schema version='{schema_version}' is not 4. "
                                 f"Only schema v4 can be updated to v5")

            # If version is 4, proceed with updates
            for query in queries:
                connection.execute(text(query))

            transaction.commit()
            print("Database updated to version 5 successfully.")
        except SQLAlchemyError as e:
            transaction.rollback()
            print(f"An error occurred: {e}")
