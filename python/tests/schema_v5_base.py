"""Schema 5 exactly as CCDB 2.4 creates it: the base of the schema 6 upgrade tests.

A frozen copy of `sqlite_table_names`, `sqlite_init_script` (ccdb/sql/sqlite_schema.py) and
`mysql_tables` (ccdb/sql/mysql_schema.py) as they stood at commit 557006e, before schema 6 changed
those modules. Never edit the copies: an upgrade test is only as good as the schema 5 it starts from.

    create_v5_sqlite(engine)   build a fresh schema 5 SQLite database on an SQLAlchemy engine
    create_v5_mysql(engine)    the same on MySQL or MariaDB, MyISAM tables as 2.4 creates them

Unlike `init_mysql_database` of 2.4, the MySQL builder commits and raises on the first error, so a
test never starts from a half-built database.
"""
from sqlalchemy import text

sqlite_table_names = ['assignments',
    'assignmentsMaterializedView',
    'columns',
    'constantSets',
    'directories',
    'eventRanges',
    'logs',
    'runRanges',
    'schemaVersions',
    'tags',
    'typeTables',
    'users',
    'variations',
    'variations_has_tags']

sqlite_init_script = """\
CREATE TABLE IF NOT EXISTS "assignments" (
  "id" integer  NOT NULL ,
  "created" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "modified" timestamp NOT NULL DEFAULT '2007-01-01 00:00:00',
  "variationId" integer NOT NULL,
  "runRangeId" integer DEFAULT NULL,
  "eventRangeId" integer DEFAULT NULL,
  "constantSetId" integer NOT NULL,
  "authorId" integer NOT NULL DEFAULT '1',
  "comment" text,
  PRIMARY KEY ("id")
);
INSERT INTO assignments VALUES(1,'2012-07-30 23:48:42','2012-07-30 23:48:42',1,1,NULL,1,2,'Test assignment for software tests');
INSERT INTO assignments VALUES(2,'2012-08-30 23:48:42','2012-08-30 23:48:42',3,2,NULL,2,2,'Test assignment for software tests 2');
INSERT INTO assignments VALUES(3,'2012-09-30 23:48:42','2012-09-30 23:48:42',3,1,NULL,3,2,'Test assignment for software tests 3');
INSERT INTO assignments VALUES(4,'2012-10-30 23:48:42','2012-10-30 23:48:42',1,1,NULL,4,2,'Test assignment for software tests 4');
INSERT INTO assignments VALUES(5,'2012-10-30 23:48:43','2012-10-30 23:48:43',4,1,NULL,5,2,'Test assignment for software tests 5');
CREATE TABLE IF NOT EXISTS "columns" (
  "id" integer NOT NULL ,
  "created" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "modified" timestamp NOT NULL DEFAULT '2007-01-01 00:00:00',
  "name" varchar(45) NOT NULL,
  "typeId" integer NOT NULL,
  "columnType" text  DEFAULT NULL,
  "order" integer NOT NULL,
  "comment" text,
  PRIMARY KEY ("id")
);
INSERT INTO columns VALUES(1,'2014-04-10 17:20:28','2014-04-10 17:20:28','x',1,'double',0,NULL);
INSERT INTO columns VALUES(2,'2014-04-10 17:20:28','2014-04-10 17:20:28','y',1,'double',1,NULL);
INSERT INTO columns VALUES(3,'2014-04-10 17:20:28','2014-04-10 17:20:28','z',1,'double',2,NULL);
INSERT INTO columns VALUES(4,'2014-04-10 17:20:28','2014-04-10 17:20:28','c1',2,'int',0,NULL);
INSERT INTO columns VALUES(5,'2014-04-10 17:20:28','2014-04-10 17:20:28','c2',2,'int',1,NULL);
INSERT INTO columns VALUES(6,'2014-04-10 17:20:28','2014-04-10 17:20:28','c3',2,'int',2,NULL);
CREATE TABLE IF NOT EXISTS "constantSets" (
  "id" integer NOT NULL ,
  "created" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "modified" timestamp NOT NULL DEFAULT '2007-01-01 00:00:00',
  "vault" longtext NOT NULL,
  "constantTypeId" integer NOT NULL,
  PRIMARY KEY ("id")
);
INSERT INTO constantSets VALUES(1,'2012-07-30 23:48:42','2012-07-30 23:48:42','1.11|1.991211|10.002|2.001|2.9912|20.111',1);
INSERT INTO constantSets VALUES(2,'2012-08-30 23:48:42','2012-08-30 23:48:42','1.0|2.0|3.0|4.0|5.0|6.0',1);
INSERT INTO constantSets VALUES(3,'2012-09-30 23:48:42','2012-09-30 23:48:42','10|20|30',2);
INSERT INTO constantSets VALUES(4,'2012-10-30 23:48:42','2012-10-30 23:48:42','2.2|2.3|2.4|2.5|2.6|2.7',1);
INSERT INTO constantSets VALUES(5,'2012-11-30 23:48:43','2012-11-30 23:48:43','10|11|12|13|14|15',1);
CREATE TABLE IF NOT EXISTS "directories" (
  "id" integer NOT NULL ,
  "created" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "modified" timestamp NOT NULL DEFAULT '2007-01-01 00:00:00',
  "name" varchar(255) NOT NULL DEFAULT '',
  "parentId" integer NOT NULL DEFAULT '0',
  "authorId" integer NOT NULL DEFAULT '1',
  "comment" text, isDeprecated TINYINT(1) NOT NULL DEFAULT 0, deprecatedByUserId INT(11) NULL DEFAULT NULL, isLocked TINYINT(1) NOT NULL DEFAULT 0, lockedByUserId INT(11) NULL DEFAULT NULL,
  PRIMARY KEY ("id")
);
INSERT INTO directories VALUES(1,'2014-04-10 17:20:28','2014-04-10 17:20:28','test',0,2,'Soft test directory',0,NULL,0,NULL);
INSERT INTO directories VALUES(2,'2014-04-10 17:20:28','2014-04-10 17:20:28','subtest',1,2,'Soft test first subdirectory',0,NULL,0,NULL);
INSERT INTO directories VALUES(3,'2014-04-10 17:20:28','2014-04-10 17:20:28','test_vars',1,2,NULL,0,NULL,0,NULL);
CREATE TABLE IF NOT EXISTS "eventRanges" (
  "id" integer NOT NULL ,
  "created" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "modified" timestamp NOT NULL DEFAULT '2007-01-01 00:00:00',
  "runNumber" integer NOT NULL,
  "eventMin" integer NOT NULL,
  "eventMax" integer NOT NULL,
  "comment" text,
  PRIMARY KEY ("id")
);
INSERT INTO eventRanges VALUES(1,'2014-04-10 17:20:28','2014-04-10 17:20:28',1,0,1000,'test');
CREATE TABLE IF NOT EXISTS "logs" (
  "id" integer NOT NULL ,
  "created" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "affectedIds" text NOT NULL,
  "action" varchar(7) NOT NULL,
  "description" varchar(255) NOT NULL,
  "comment" text,
  "authorId" integer NOT NULL,
  PRIMARY KEY ("id")
);
INSERT INTO logs VALUES(1,'2014-04-10 17:20:28','users_1','create','Created user ''anonymous''','User anonymous is a default user for CCDB. It has no modify privilegies',1);
INSERT INTO logs VALUES(2,'2016-09-16 00:34:16.538294','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',1);
INSERT INTO logs VALUES(3,'2016-09-16 00:34:17.089200','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',1);
INSERT INTO logs VALUES(4,'2016-09-16 00:34:44.337341','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',1);
INSERT INTO logs VALUES(5,'2016-09-16 00:34:44.796758','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',1);
INSERT INTO logs VALUES(6,'2019-04-18 12:57:33.396440','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',2);
INSERT INTO logs VALUES(7,'2019-04-18 13:08:44.354750','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',2);
INSERT INTO logs VALUES(8,'2019-06-11 14:10:09.751258','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',2);
INSERT INTO logs VALUES(9,'2019-06-11 14:10:10.634549','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',2);
INSERT INTO logs VALUES(10,'2019-06-12 13:06:49.937498','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',2);
INSERT INTO logs VALUES(11,'2019-06-12 15:49:16.744217','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',2);
INSERT INTO logs VALUES(12,'2019-06-12 15:53:44.437710','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',2);
INSERT INTO logs VALUES(13,'2019-06-12 15:58:27.521110','|directories5|','create','Created directory ''/test/testdir/constants''','My constants',2);
CREATE TABLE IF NOT EXISTS "runRanges" (
  "id" integer NOT NULL ,
  "created" timestamp NOT NULL DEFAULT '2007-01-01 00:00:00',
  "modified" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "name" varchar(45) DEFAULT '',
  "runMin" integer NOT NULL,
  "runMax" integer NOT NULL,
  "comment" text,
  PRIMARY KEY ("id")
);
INSERT INTO runRanges VALUES(1,'2014-04-10 17:20:28','2014-04-10 17:20:28','all',0,2147483647,'Default runrange that covers all runs');
INSERT INTO runRanges VALUES(2,'2014-04-10 17:20:28','2014-04-10 17:20:28','test',500,3000,'Test runrange for software tests');
INSERT INTO runRanges VALUES(3,'2014-04-10 17:20:28','2014-04-10 17:20:28','',0,2000,'Test runrange. Secont test runrange for software test');
INSERT INTO runRanges VALUES(4,'2016-09-16 00:34:16.442248','2016-09-16 00:34:16.442248','',0,1000,'');
CREATE TABLE IF NOT EXISTS "schemaVersions" (
  "id" integer NOT NULL,
  "schemaVersion" integer NOT NULL DEFAULT '1',
  PRIMARY KEY ("id")
);
INSERT INTO schemaVersions VALUES(1,5);
CREATE TABLE IF NOT EXISTS "tags" (
  "id" integer NOT NULL ,
  "name" varchar(45) NOT NULL,
  PRIMARY KEY ("id")
);
CREATE TABLE IF NOT EXISTS "typeTables" (
  "id" integer NOT NULL ,
  "created" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "modified" timestamp NOT NULL DEFAULT '2007-01-01 00:00:00',
  "directoryId" integer NOT NULL,
  "name" varchar(255) NOT NULL,
  "nRows" integer NOT NULL DEFAULT '1',
  "nColumns" integer NOT NULL,
  "nAssignments" integer NOT NULL DEFAULT '0',
  "authorId" integer NOT NULL DEFAULT '1',
  "comment" text, isDeprecated TINYINT(1) NOT NULL DEFAULT 0, deprecatedByUserId INT(11) NULL DEFAULT NULL, isLocked TINYINT(1) NOT NULL DEFAULT 0, lockedByUserId INT(11) NULL DEFAULT NULL, lockTime TIMESTAMP NULL DEFAULT NULL,
  PRIMARY KEY ("id")
);
INSERT INTO typeTables VALUES(1,'2014-04-10 17:20:28','2014-04-10 17:20:28',3,'test_table',2,3,2,2,'Test type',0,NULL,0,NULL,NULL);
INSERT INTO typeTables VALUES(2,'2014-04-10 17:20:28','2014-04-10 17:20:28',3,'test_table2',1,3,1,2,'Test type 2',0,NULL,0,NULL,NULL);
CREATE TABLE IF NOT EXISTS "users" (
  "id" integer NOT NULL ,
  "created" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "lastActionTime" timestamp NOT NULL DEFAULT '2001-01-01 00:00:00',
  "name" varchar(100) NOT NULL,
  "password" varchar(100) DEFAULT NULL,
  "roles" text NOT NULL,
  "info" varchar(125) NOT NULL,
  "isDeleted" integer NOT NULL DEFAULT '0',
  PRIMARY KEY ("id")
);
INSERT INTO users VALUES(1,'2014-04-10 17:20:28','2016-09-16 00:34:44.794743','anonymous',NULL,'','User anonymous is a default user for CCDB. It has no modify privilegies',0);
INSERT INTO users VALUES(2,'2012-07-15 15:16:30','2019-06-12 15:58:27.518610','test_user','test','runrange_crate,runrange_delete','User for unit tests',0);
CREATE TABLE IF NOT EXISTS "variations" (
  "id" integer NOT NULL ,
  "created" timestamp NOT NULL DEFAULT '2007-01-01 00:00:00',
  "modified" timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "name" varchar(100) NOT NULL DEFAULT 'default',
  "description" varchar(255) DEFAULT NULL,
  "authorId" integer NOT NULL DEFAULT '1',
  "comment" text,
  "parentId" integer NOT NULL DEFAULT '0', isLocked TINYINT(1) NOT NULL DEFAULT 0, lockTime TIMESTAMP NULL DEFAULT NULL, lockedByUserId INT(11) NULL DEFAULT NULL, goBackBehavior INT(11) NOT NULL DEFAULT 0, goBackTime TIMESTAMP NULL DEFAULT NULL, isDeprecated TINYINT(1) NOT NULL DEFAULT 0, deprecatedByUserId INT(11) NULL DEFAULT NULL,
  PRIMARY KEY ("id")
);
INSERT INTO variations VALUES(1,'2014-04-10 17:20:28','2014-04-10 17:20:28','default','Default variation',2,'Default variation',0,0,NULL,NULL,0,NULL,0,NULL);
INSERT INTO variations VALUES(2,'2014-04-10 17:20:28','2014-04-10 17:20:28','mc','Mone-Carlo variations',2,'Monte-Carlo specific variation',1,0,NULL,NULL,0,NULL,0,NULL);
INSERT INTO variations VALUES(3,'2014-04-10 17:20:28','2014-04-10 17:20:28','test','Test variation',2,'Variation for software test',1,0,NULL,NULL,0,NULL,0,NULL);
INSERT INTO variations VALUES(4,'2014-04-10 17:20:28','2014-04-10 17:20:28','subtest','Test variation of second level',2,'Variation for software test which has test variation as parent',3,0,NULL,NULL,0,NULL,0,NULL);
CREATE TABLE IF NOT EXISTS "variations_has_tags" (
  "variations_id" integer NOT NULL,
  "tags_id" integer NOT NULL,
  PRIMARY KEY ("variations_id","tags_id")
);
CREATE TABLE assignmentsMaterializedView (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assignmentsId INTEGER NOT NULL,
            variationsId INTEGER NOT NULL,
            constantSetsId INTEGER NOT NULL,
            typeTablesId INTEGER NOT NULL,
            runRangesId INTEGER NOT NULL,
            runMin INTEGER NOT NULL,
            runMax INTEGER NOT NULL,
            assignmentTime TIMESTAMP NOT NULL
        );
CREATE INDEX "variations_has_tags_fk_variations_has_tags_tags1_idx" ON "variations_has_tags" ("tags_id");
CREATE INDEX "typeTables_id_UNIQUE" ON "typeTables" ("id");
CREATE INDEX "typeTables_fk_constantTypes_directories1_idx" ON "typeTables" ("directoryId");
CREATE INDEX "users_id_UNIQUE" ON "users" ("id");
CREATE INDEX "assignments_id_UNIQUE" ON "assignments" ("id");
CREATE INDEX "assignments_fk_assignments_variations1_idx" ON "assignments" ("variationId");
CREATE INDEX "assignments_fk_assignments_runRanges1_idx" ON "assignments" ("runRangeId");
CREATE INDEX "assignments_fk_assignments_constantSets1_idx" ON "assignments" ("constantSetId");
CREATE INDEX "assignments_fk_assignments_eventRanges1_idx" ON "assignments" ("eventRangeId");
CREATE INDEX "assignments_date_sort_index" ON "assignments" ("created");
CREATE INDEX "tags_id_UNIQUE" ON "tags" ("id");
CREATE INDEX "columns_id_UNIQUE" ON "columns" ("id");
CREATE INDEX "columns_fk_columns_constantTypes1_idx" ON "columns" ("typeId");
CREATE INDEX "directories_id_UNIQUE" ON "directories" ("id");
CREATE INDEX "directories_fk_directories_directories1_idx" ON "directories" ("parentId");
CREATE INDEX "variations_id_UNIQUE" ON "variations" ("id");
CREATE INDEX "variations_name_search" ON "variations" ("name");
CREATE INDEX "variations_fk_variations_variations1_idx" ON "variations" ("parentId");
CREATE INDEX "runRanges_id_UNIQUE" ON "runRanges" ("id");
CREATE INDEX "runRanges_run search" ON "runRanges" ("runMin","runMax");
CREATE INDEX "eventRanges_ideventRanges_UNIQUE" ON "eventRanges" ("id");
CREATE INDEX "constantSets_id_UNIQUE" ON "constantSets" ("id");
CREATE INDEX "constantSets_fk_constantSets_constantTypes1_idx" ON "constantSets" ("constantTypeId");
CREATE INDEX "logs_id_UNIQUE" ON "logs" ("id");
CREATE INDEX "logs_fk_logs_users1_idx" ON "logs" ("authorId");
"""

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


def _sqlite_statements(script):
    """Statements of the script, one per ';' at a line end, as 2.4's init_sqlite_database splits it."""
    statement = []
    for line in script.splitlines():
        if not line.strip():
            continue
        statement.append(line)
        if line.rstrip().endswith(";"):
            yield "\n".join(statement)
            statement = []


def create_v5_sqlite(engine):
    with engine.begin() as connection:
        for table_name in sqlite_table_names:
            connection.execute(text(f'DROP TABLE IF EXISTS "{table_name}"'))
        for statement in _sqlite_statements(sqlite_init_script):
            connection.execute(text(statement))


def create_v5_mysql(engine):
    with engine.begin() as connection:
        for commands in mysql_tables.values():
            for key in ("drop", "create"):
                if key in commands:
                    connection.execute(text(commands[key]))
            for insert_query in commands.get("data", []):
                connection.execute(text(insert_query))
