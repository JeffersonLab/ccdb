from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError


mysql_tables = {

    # constantSets = data storage
    "constantSets": {
        "drop": "DROP TABLE IF EXISTS `constantSets` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `constantSets` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000,
                `vault` LONGTEXT NOT NULL,
                `constantTypeId` INT NOT NULL,
                PRIMARY KEY (`id`),
                UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
                INDEX `fk_constantSets_constantTypes1_idx` (`constantTypeId` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (1, '2012-07-30 23:48:42', '2012-07-30 23:48:42', '1.11|1.991211|10.002|2.001|2.9912|20.111', 1);",
            "INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (2, '2012-08-30 23:48:42', '2012-08-30 23:48:42', '1.0|2.0|3.0|4.0|5.0|6.0', 1);",
            "INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (3, '2012-09-30 23:48:42', '2012-09-30 23:48:42', '10|20|30', 2);",
            "INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (4, '2012-10-30 23:48:42', '2012-10-30 23:48:42', '2.2|2.3|2.4|2.5|2.6|2.7', 1);",
            "INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (5, '2012-11-30 23:48:43', '2012-11-30 23:48:43', '10|11|12|13|14|15', 1);",

        ]
    },

    # DATA HEADER (ASSIGNMENTS)
    "assignments": {
        "drop": "DROP TABLE IF EXISTS `assignments` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `assignments` (
                `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
                `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000,
                `variationId` INT NOT NULL,
                `runRangeId` INT NULL,
                `eventRangeId` INT NULL,
                `authorId` INT NOT NULL DEFAULT 1,
                `comment` TEXT NULL,
                `constantSetId` INT NOT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_assignments_variations1_idx` (`variationId` ASC) VISIBLE,
                INDEX `fk_assignments_runRanges1_idx` (`runRangeId` ASC) VISIBLE,
                INDEX `fk_assignments_eventRanges1_idx` (`eventRangeId` ASC) VISIBLE,
                UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
                INDEX `date_sort_index` USING BTREE (`created`) VISIBLE,
                INDEX `fk_assignments_constantSets1_idx` (`constantSetId` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `authorId`, `comment`, `constantSetId`) VALUES (1, '2012-07-30 23:48:42', '2012-07-30 23:48:42', 1, 1, NULL, 2, 'Test assignment for software tests', 1);",
            "INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `authorId`, `comment`, `constantSetId`) VALUES (2, '2012-08-30 23:48:42', '2012-08-30 23:48:42', 3, 2, NULL, 2, 'Test assignment for software tests 2', 2);",
            "INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `authorId`, `comment`, `constantSetId`) VALUES (3, '2012-09-30 23:48:42', '2012-09-30 23:48:42', 3, 1, NULL, 2, 'Test assignment for software tests 3', 3);",
            "INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `authorId`, `comment`, `constantSetId`) VALUES (4, '2012-10-30 23:48:42', '2012-10-30 23:48:42', 1, 1, NULL, 2, 'Test assignment for software tests 4', 4);",
            "INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `authorId`, `comment`, `constantSetId`) VALUES (5, '2012-10-30 23:48:43', '2012-10-30 23:48:43', 4, 1, NULL, 2, 'Test assignment for software tests 5', 5);",
        ]
    },
    "runRanges": {
        "drop": "DROP TABLE IF EXISTS `runRanges`;",
        "create": """
            CREATE TABLE IF NOT EXISTS `runRanges` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `created` TIMESTAMP NOT NULL DEFAULT 20070101000000,
                `modified` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `name` VARCHAR(45) NULL DEFAULT '',
                `runMin` INT NOT NULL,
                `runMax` INT NOT NULL,
                `comment` TEXT NULL DEFAULT NULL,
                PRIMARY KEY (`id`),
                UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
                INDEX `run search` (`runMin` ASC, `runMax` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (1, DEFAULT, DEFAULT, 'all', 0, 2147483647, 'Default runrange that covers all runs');",
            "INSERT INTO `runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (2, DEFAULT, DEFAULT, 'test', 500, 3000, 'Test runrange for software tests');",
            "INSERT INTO `runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (3, DEFAULT, DEFAULT, '', 0, 2000, 'Test runrange. Secont test runrange for software test');",
        ]
    },
    "eventRanges": {
        "drop": "DROP TABLE IF EXISTS `eventRanges` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `eventRanges` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000,
                `runNumber` INT NOT NULL,
                `eventMin` INT NOT NULL,
                `eventMax` INT NOT NULL,
                `comment` TEXT NULL DEFAULT NULL,
                PRIMARY KEY (`id`),
                UNIQUE INDEX `ideventRanges_UNIQUE` (`id` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `eventRanges` (`id`, `created`, `modified`, `runNumber`, `eventMin`, `eventMax`, `comment`) VALUES (1, DEFAULT, DEFAULT, 1, 0, 1000, 'test');"
        ]
    },
    # -- Variations table --
    "variations": {
        "drop": "DROP TABLE IF EXISTS `variations` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `variations` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `created` TIMESTAMP NOT NULL DEFAULT 20070101000000,
                `modified` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `name` VARCHAR(100) NOT NULL DEFAULT 'default',
                `description` VARCHAR(255) NULL,
                `authorId` INT NOT NULL DEFAULT 1,
                `comment` TEXT NULL DEFAULT NULL,
                `parentId` INT NOT NULL DEFAULT 1,
                `isLocked` TINYINT(1) NOT NULL DEFAULT 0,
                `lockTime` TIMESTAMP NULL DEFAULT NULL,
                `lockedByUserId` INT NULL DEFAULT NULL,
                `goBackBehavior` INT NOT NULL DEFAULT 0,
                `goBackTime` TIMESTAMP NULL DEFAULT NULL,
                `isDeprecated` TINYINT(1) NOT NULL DEFAULT 0,
                `deprecatedByUserId` INT NULL DEFAULT NULL,
                PRIMARY KEY (`id`),
                UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
                INDEX `name_search` USING HASH (`name`) VISIBLE,
                INDEX `fk_variations_variations1_idx` (`parentId` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`, `isLocked`, `lockTime`, `lockedByUserId`, `goBackBehavior`, `goBackTime`, `isDeprecated`, `deprecatedByUserId`) VALUES (1, DEFAULT, DEFAULT, 'default', 'Default variation', 2, 'Default variation', 0, DEFAULT, NULL, NULL, DEFAULT, NULL, DEFAULT, NULL);",
            "INSERT INTO `variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`, `isLocked`, `lockTime`, `lockedByUserId`, `goBackBehavior`, `goBackTime`, `isDeprecated`, `deprecatedByUserId`) VALUES (2, DEFAULT, DEFAULT, 'mc', 'Mone-Carlo variations', 2, 'Monte-Carlo specific variation', 1, DEFAULT, NULL, NULL, DEFAULT, NULL, DEFAULT, NULL);",
            "INSERT INTO `variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`, `isLocked`, `lockTime`, `lockedByUserId`, `goBackBehavior`, `goBackTime`, `isDeprecated`, `deprecatedByUserId`) VALUES (3, DEFAULT, DEFAULT, 'test', 'Test variation', 2, 'Variation for software test', 1, DEFAULT, NULL, NULL, DEFAULT, NULL, DEFAULT, NULL);",
            "INSERT INTO `variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`, `isLocked`, `lockTime`, `lockedByUserId`, `goBackBehavior`, `goBackTime`, `isDeprecated`, `deprecatedByUserId`) VALUES (4, DEFAULT, DEFAULT, 'subtest', 'Test variation of second level', 2, 'Variation for software test which has test variation as parent', 3, DEFAULT, NULL, NULL, DEFAULT, NULL, DEFAULT, NULL);",
        ]
    },
    # Name-PATH
    "directories": {
        "drop": "DROP TABLE IF EXISTS `directories` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `directories` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000,
                `name` VARCHAR(255) NOT NULL DEFAULT '',
                `parentId` INT NOT NULL DEFAULT 0,
                `authorId` INT NOT NULL DEFAULT 1,
                `comment` TEXT NULL DEFAULT NULL,
                `isDeprecated` TINYINT(1) NOT NULL DEFAULT 0,
                `deprecatedByUserId` INT NULL DEFAULT NULL,
                `isLocked` TINYINT(1) NOT NULL DEFAULT 0,
                `lockedByUserId` INT NULL,
                PRIMARY KEY (`id`),
                INDEX `fk_directories_directories1_idx` (`parentId` ASC) VISIBLE,
                UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`, `isDeprecated`, `deprecatedByUserId`, `isLocked`, `lockedByUserId`) VALUES (1, DEFAULT, DEFAULT, 'test', 0, 2, 'Soft test directory', DEFAULT, NULL, DEFAULT, NULL);",
            "INSERT INTO `directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`, `isDeprecated`, `deprecatedByUserId`, `isLocked`, `lockedByUserId`) VALUES (2, DEFAULT, DEFAULT, 'subtest', 1, 2, 'Soft test first subdirectory', DEFAULT, NULL, DEFAULT, NULL);",
            "INSERT INTO `directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`, `isDeprecated`, `deprecatedByUserId`, `isLocked`, `lockedByUserId`) VALUES (3, DEFAULT, DEFAULT, 'test_vars', 1, 2, NULL, DEFAULT, NULL, DEFAULT, NULL);",
        ]
    },
    "typeTables": {
        "drop": "DROP TABLE IF EXISTS `typeTables` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `typeTables` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000,
                `directoryId` INT NOT NULL,
                `name` VARCHAR(255) NOT NULL,
                `nRows` INT NOT NULL DEFAULT 1,
                `nColumns` INT NOT NULL,
                `nAssignments` INT NOT NULL DEFAULT 0,
                `authorId` INT NOT NULL DEFAULT 1,
                `comment` TEXT NULL DEFAULT NULL,
                `isDeprecated` TINYINT(1) NOT NULL DEFAULT 0,
                `deprecatedByUserId` INT NULL DEFAULT NULL,
                `isLocked` TINYINT(1) NOT NULL DEFAULT 0,
                `lockedByUserId` INT NULL DEFAULT NULL,
                `lockTime` TIMESTAMP NULL DEFAULT NULL,
                PRIMARY KEY (`id`),
                UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
                INDEX `fk_constantTypes_directories1_idx` (`directoryId` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `typeTables` (`id`, `created`, `modified`, `directoryId`, `name`, `nRows`, `nColumns`, `nAssignments`, `authorId`, `comment`, `isDeprecated`, `deprecatedByUserId`, `isLocked`, `lockedByUserId`, `lockTime`) VALUES (1, DEFAULT, DEFAULT, 3, 'test_table', 2, 3, 2, 2, 'Test type', DEFAULT, NULL, DEFAULT, NULL, NULL);",
            "INSERT INTO `typeTables` (`id`, `created`, `modified`, `directoryId`, `name`, `nRows`, `nColumns`, `nAssignments`, `authorId`, `comment`, `isDeprecated`, `deprecatedByUserId`, `isLocked`, `lockedByUserId`, `lockTime`) VALUES (2, DEFAULT, DEFAULT, 3, 'test_table2', 1, 3, 1, 2, 'Test type 2', DEFAULT, NULL, DEFAULT, NULL, NULL);",
        ]
    },
    "columns": {
        "drop": "DROP TABLE IF EXISTS `columns` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `columns` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000,
                `name` VARCHAR(45) NOT NULL,
                `typeId` INT NOT NULL,
                `columnType` ENUM('int', 'uint','long','ulong','double','string','bool') NULL,
                `order` INT NOT NULL,
                `comment` TEXT NULL DEFAULT NULL,
                PRIMARY KEY (`id`),
                UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
                INDEX `fk_columns_constantTypes1_idx` (`typeId` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'x', 1, 'double', 0, NULL);",
            "INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'y', 1, 'double', 1, NULL);",
            "INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'z', 1, 'double', 2, NULL);",
            "INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'c1', 2, 'int', 0, NULL);",
            "INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'c2', 2, 'int', 1, NULL);",
            "INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'c3', 2, 'int', 2, NULL);",
        ]
    },

    "tags": {
        "drop": "DROP TABLE IF EXISTS `tags` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `tags` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `name` VARCHAR(45) NOT NULL,
                PRIMARY KEY (`id`),
                UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [

        ]
    },
    "variationsToTags": {
        "drop": "DROP TABLE IF EXISTS `variationsToTags` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `variationsToTags` (
                `variations_id` INT NOT NULL,
                `tags_id` INT NOT NULL,
                PRIMARY KEY (`variations_id`, `tags_id`),
                INDEX `fk_variations_has_tags_tags1_idx` (`tags_id` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [

        ]
    },

    # CCDB Meta data
    "users": {
        "drop": "DROP TABLE IF EXISTS `users` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `users` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `lastActionTime` TIMESTAMP NOT NULL DEFAULT 00010101000000,
                `name` VARCHAR(100) NOT NULL,
                `password` VARCHAR(100) NULL,
                `roles` TEXT NOT NULL,
                `info` VARCHAR(125) NOT NULL,
                `isDeleted` TINYINT(1) NOT NULL DEFAULT 0,
                PRIMARY KEY (`id`),
                UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `users` (`id`, `created`, `lastActionTime`, `name`, `password`, `roles`, `info`, `isDeleted`) VALUES (1, DEFAULT, DEFAULT, 'anonymous', NULL, '', 'User anonymous is a default user for CCDB. It has no modify privilegies', 0);",
            "INSERT INTO `users` (`id`, `created`, `lastActionTime`, `name`, `password`, `roles`, `info`, `isDeleted`) VALUES (2, '2012-07-15 15:16:30', '2012-09-20 08:11:12', 'test_user', 'test', 'runrange_crate,runrange_delete', 'User for unit tests', 0);",

        ]
    },
    "logs": {
        "drop": "DROP TABLE IF EXISTS `logs` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `logs` (
                `id` INT NOT NULL AUTO_INCREMENT,
                `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                `affectedIds` TEXT NOT NULL,
                `action` VARCHAR(7) NOT NULL,
                `description` VARCHAR(255) NOT NULL,
                `comment` TEXT NULL,
                `authorId` INT NOT NULL,
                PRIMARY KEY (`id`),
                UNIQUE INDEX `id_UNIQUE` (`id` ASC) VISIBLE,
                INDEX `fk_logs_users1_idx` (`authorId` ASC) VISIBLE)
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `logs` (`id`, `created`, `affectedIds`, `action`, `description`, `comment`, `authorId`) VALUES (1, DEFAULT, 'users_1', 'create', 'Created user anonymous', 'User anonymous is a default user for CCDB. It has no modify privilegies', 1);"
        ]
    },
    "schemaVersions": {
        "drop": "DROP TABLE IF EXISTS `schemaVersions` ;",
        "create": """
            CREATE TABLE IF NOT EXISTS `schemaVersions` (
                `id` INT NOT NULL,
                `schemaVersion` INT NOT NULL DEFAULT 1,
                PRIMARY KEY (`id`))
                ENGINE = MyISAM;
        """,
        "data": [
            "INSERT INTO `schemaVersions` (`id`, `schemaVersion`) VALUES (1, 5);"
        ]
    },
    "assignmentsMaterializedView": {
        "drop": "DROP TABLE IF EXISTS `assignmentsMaterializedView` ;",
        "create": """
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
        "data": [

        ]
    },
}


def init_mysql_database(db_url, tables_dict=None):
    """
    Setup a database schema and fill it with data based on the provided dictionary.

    :param engine: SQLAlchemy engine or connection to the database.
    :param tables_dict: A dictionary containing the SQL commands to drop, create tables, and insert data.
    """
    if tables_dict is None:
        tables_dict = mysql_tables
    engine = create_engine(db_url)
    with engine.connect() as connection:
        for table_name, commands in tables_dict.items():
            try:
                # Drop the existing table if it exists
                if 'drop' in commands:
                    connection.execute(commands['drop'])

                # Create the table
                if 'create' in commands:
                    connection.execute(commands['create'])

                # Insert data into the table
                if 'data' in commands:
                    for insert_query in commands['data']:
                        connection.execute(insert_query)

                print(f"Table {table_name} processed successfully.")
            except SQLAlchemyError as e:
                print(f"Error processing table {table_name}: {str(e)}")

def generate_mysql_sql_file(tables_dict, file_path='mysql_setup.sql'):
    """
    Generate a MySQL .sql file with drop, create, and insert commands
    based on the provided dictionary.

    :param tables_dict: Dictionary with table definitions and operations.
    :param file_path: Path to the .sql file to be generated.
    """
    with open(file_path, 'w') as sql_file:
        for table_name, commands in tables_dict.items():
            sql_file.write(f"-- Processing table: {table_name}\n")

            # Drop the existing table if it exists
            if 'drop' in commands:
                sql_file.write(f"{commands['drop']}\n")

            # Create the table
            if 'create' in commands:
                sql_file.write(f"{commands['create']}\n")

            # Insert data into the table
            if 'data' in commands:
                for insert_query in commands['data']:
                    sql_file.write(f"{insert_query}\n")

            # Add a separator for readability
            sql_file.write("\n\n")

    print(f"SQL file '{file_path}' has been generated successfully.")