-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

-- -----------------------------------------------------
-- Schema ccdb
-- -----------------------------------------------------
DROP SCHEMA IF EXISTS `ccdb` ;

-- -----------------------------------------------------
-- Schema ccdb
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `ccdb` DEFAULT CHARACTER SET latin1 ;
USE `ccdb` ;

-- -----------------------------------------------------
-- Table `runRanges`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `runRanges` ;

CREATE TABLE IF NOT EXISTS `runRanges` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `created` TIMESTAMP NOT NULL DEFAULT 20070101000000,
  `modified` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `name` VARCHAR(45) NULL DEFAULT '',
  `runMin` INT NOT NULL,
  `runMax` INT NOT NULL,
  `comment` TEXT NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC),
  INDEX `run search` (`runMin` ASC, `runMax` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `variations`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `variations` ;

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
  `lockAuthorId` VARCHAR(45) NULL DEFAULT NULL,
  `goBackBehavior` INT NOT NULL DEFAULT 0,
  `goBackTime` TIMESTAMP NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC),
  INDEX `name_search` USING HASH (`name` ASC),
  INDEX `fk_variations_variations1_idx` (`parentId` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `eventRanges`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `eventRanges` ;

CREATE TABLE IF NOT EXISTS `eventRanges` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000,
  `runNumber` INT NOT NULL,
  `eventMin` INT NOT NULL,
  `eventMax` INT NOT NULL,
  `comment` TEXT NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `ideventRanges_UNIQUE` (`id` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `directories`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `directories` ;

CREATE TABLE IF NOT EXISTS `directories` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000,
  `name` VARCHAR(255) NOT NULL DEFAULT '',
  `parentId` INT NOT NULL DEFAULT 0,
  `authorId` INT NOT NULL DEFAULT 1,
  `comment` TEXT NULL DEFAULT NULL,
  `isDeprecated` TINYINT(1) NOT NULL DEFAULT 0,
  `deprecatedById` INT NOT NULL DEFAULT -1,
  PRIMARY KEY (`id`),
  INDEX `fk_directories_directories1_idx` (`parentId` ASC),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `typeTables`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `typeTables` ;

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
  `deprecatedById` INT NOT NULL DEFAULT -1,
  `isLocked` TINYINT(1) NOT NULL DEFAULT 0,
  `lockAuthorId` INT NULL DEFAULT NULL,
  `lockTime` TIMESTAMP NULL DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC),
  INDEX `fk_constantTypes_directories1_idx` (`directoryId` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `constantSets`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `constantSets` ;

CREATE TABLE IF NOT EXISTS `constantSets` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000,
  `vault` LONGTEXT NOT NULL,
  `constantTypeId` INT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC),
  INDEX `fk_constantSets_constantTypes1_idx` (`constantTypeId` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `assignments`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `assignments` ;

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
  INDEX `fk_assignments_variations1_idx` (`variationId` ASC),
  INDEX `fk_assignments_runRanges1_idx` (`runRangeId` ASC),
  INDEX `fk_assignments_eventRanges1_idx` (`eventRangeId` ASC),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC),
  INDEX `date_sort_index` USING BTREE (`created` DESC),
  INDEX `fk_assignments_constantSets1_idx` (`constantSetId` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `columns`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `columns` ;

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
  UNIQUE INDEX `id_UNIQUE` (`id` ASC),
  INDEX `fk_columns_constantTypes1_idx` (`typeId` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `tags`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `tags` ;

CREATE TABLE IF NOT EXISTS `tags` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(45) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `variations_has_tags`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `variations_has_tags` ;

CREATE TABLE IF NOT EXISTS `variations_has_tags` (
  `variations_id` INT NOT NULL,
  `tags_id` INT NOT NULL,
  PRIMARY KEY (`variations_id`, `tags_id`),
  INDEX `fk_variations_has_tags_tags1_idx` (`tags_id` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `users`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `users` ;

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
  UNIQUE INDEX `id_UNIQUE` (`id` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `logs`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `logs` ;

CREATE TABLE IF NOT EXISTS `logs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `affectedIds` TEXT NOT NULL,
  `action` VARCHAR(7) NOT NULL,
  `description` VARCHAR(255) NOT NULL,
  `comment` TEXT NULL,
  `authorId` INT NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC),
  INDEX `fk_logs_users1_idx` (`authorId` ASC))
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `schemaVersions`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `schemaVersions` ;

CREATE TABLE IF NOT EXISTS `schemaVersions` (
  `id` INT NOT NULL,
  `schemaVersion` INT NOT NULL DEFAULT 1,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `user`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `user` ;

CREATE TABLE IF NOT EXISTS `user` (
  `username` VARCHAR(16) NOT NULL,
  `email` VARCHAR(255) NULL,
  `password` VARCHAR(32) NOT NULL,
  `create_time` TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP);


-- -----------------------------------------------------
-- Table `assignmentsMaterializedView`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `assignmentsMaterializedView` ;

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
  INDEX `fk_assignmentsMaterializedView_assignments1_idx` (`assignmentsId` ASC),
  INDEX `fk_assignmentsMaterializedView_variations1_idx` (`variationsId` ASC),
  INDEX `fk_assignmentsMaterializedView_constantSets1_idx` (`constantSetsId` ASC),
  INDEX `fk_assignmentsMaterializedView_typeTables1_idx` (`typeTablesId` ASC),
  PRIMARY KEY (`id`),
  UNIQUE INDEX `id_UNIQUE` (`id` ASC),
  INDEX `fk_assignmentsMaterializedView_runRanges1_idx` (`runRangesId` ASC),
  CONSTRAINT `fk_assignmentsMaterializedView_assignments1`
    FOREIGN KEY (`assignmentsId`)
    REFERENCES `assignments` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_assignmentsMaterializedView_variations1`
    FOREIGN KEY (`variationsId`)
    REFERENCES `variations` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_assignmentsMaterializedView_constantSets1`
    FOREIGN KEY (`constantSetsId`)
    REFERENCES `constantSets` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_assignmentsMaterializedView_typeTables1`
    FOREIGN KEY (`typeTablesId`)
    REFERENCES `typeTables` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION,
  CONSTRAINT `fk_assignmentsMaterializedView_runRanges1`
    FOREIGN KEY (`runRangesId`)
    REFERENCES `runRanges` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;

-- -----------------------------------------------------
-- Data for table `runRanges`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (1, DEFAULT, DEFAULT, 'all', 0, 2147483647, 'Default runrange that covers all runs');
INSERT INTO `runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (2, DEFAULT, DEFAULT, 'test', 500, 3000, 'Test runrange for software tests');
INSERT INTO `runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (3, DEFAULT, DEFAULT, '', 0, 2000, 'Test runrange. Secont test runrange for software test');

COMMIT;


-- -----------------------------------------------------
-- Data for table `variations`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`, `isLocked`, `lockTime`, `lockAuthorId`, `goBackBehavior`, `goBackTime`) VALUES (1, DEFAULT, DEFAULT, 'default', 'Default variation', 2, 'Default variation', 0, DEFAULT, NULL, NULL, DEFAULT, NULL);
INSERT INTO `variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`, `isLocked`, `lockTime`, `lockAuthorId`, `goBackBehavior`, `goBackTime`) VALUES (2, DEFAULT, DEFAULT, 'mc', 'Mone-Carlo variations', 2, 'Monte-Carlo specific variation', 1, DEFAULT, NULL, NULL, DEFAULT, NULL);
INSERT INTO `variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`, `isLocked`, `lockTime`, `lockAuthorId`, `goBackBehavior`, `goBackTime`) VALUES (3, DEFAULT, DEFAULT, 'test', 'Test variation', 2, 'Variation for software test', 1, DEFAULT, NULL, NULL, DEFAULT, NULL);
INSERT INTO `variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`, `isLocked`, `lockTime`, `lockAuthorId`, `goBackBehavior`, `goBackTime`) VALUES (4, DEFAULT, DEFAULT, 'subtest', 'Test variation of second level', 2, 'Variation for software test which has test variation as parent', 3, DEFAULT, NULL, NULL, DEFAULT, NULL);

COMMIT;


-- -----------------------------------------------------
-- Data for table `eventRanges`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `eventRanges` (`id`, `created`, `modified`, `runNumber`, `eventMin`, `eventMax`, `comment`) VALUES (1, DEFAULT, DEFAULT, 1, 0, 1000, 'test');

COMMIT;


-- -----------------------------------------------------
-- Data for table `directories`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`, `isDeprecated`, `deprecatedById`) VALUES (1, DEFAULT, DEFAULT, 'test', 0, 2, 'Soft test directory', DEFAULT, DEFAULT);
INSERT INTO `directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`, `isDeprecated`, `deprecatedById`) VALUES (2, DEFAULT, DEFAULT, 'subtest', 1, 2, 'Soft test first subdirectory', DEFAULT, DEFAULT);
INSERT INTO `directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`, `isDeprecated`, `deprecatedById`) VALUES (3, DEFAULT, DEFAULT, 'test_vars', 1, 2, NULL, DEFAULT, DEFAULT);

COMMIT;


-- -----------------------------------------------------
-- Data for table `typeTables`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `typeTables` (`id`, `created`, `modified`, `directoryId`, `name`, `nRows`, `nColumns`, `nAssignments`, `authorId`, `comment`, `isDeprecated`, `deprecatedById`, `isLocked`, `lockAuthorId`, `lockTime`) VALUES (1, DEFAULT, DEFAULT, 3, 'test_table', 2, 3, 2, 2, 'Test type', DEFAULT, DEFAULT, DEFAULT, NULL, NULL);
INSERT INTO `typeTables` (`id`, `created`, `modified`, `directoryId`, `name`, `nRows`, `nColumns`, `nAssignments`, `authorId`, `comment`, `isDeprecated`, `deprecatedById`, `isLocked`, `lockAuthorId`, `lockTime`) VALUES (2, DEFAULT, DEFAULT, 3, 'test_table2', 1, 3, 1, 2, 'Test type 2', DEFAULT, DEFAULT, DEFAULT, NULL, NULL);

COMMIT;


-- -----------------------------------------------------
-- Data for table `constantSets`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (1, '2012-07-30 23:48:42', '2012-07-30 23:48:42', '1.11|1.991211|10.002|2.001|2.9912|20.111', 1);
INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (2, '2012-08-30 23:48:42', '2012-08-30 23:48:42', '1.0|2.0|3.0|4.0|5.0|6.0', 1);
INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (3, '2012-09-30 23:48:42', '2012-09-30 23:48:42', '10|20|30', 2);
INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (4, '2012-10-30 23:48:42', '2012-10-30 23:48:42', '2.2|2.3|2.4|2.5|2.6|2.7', 1);
INSERT INTO `constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (5, '2012-11-30 23:48:43', '2012-11-30 23:48:43', '10|11|12|13|14|15', 1);

COMMIT;


-- -----------------------------------------------------
-- Data for table `assignments`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `authorId`, `comment`, `constantSetId`) VALUES (1, '2012-07-30 23:48:42', '2012-07-30 23:48:42', 1, 1, NULL, 2, 'Test assignment for software tests', 1);
INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `authorId`, `comment`, `constantSetId`) VALUES (2, '2012-08-30 23:48:42', '2012-08-30 23:48:42', 3, 2, NULL, 2, 'Test assignment for software tests 2', 2);
INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `authorId`, `comment`, `constantSetId`) VALUES (3, '2012-09-30 23:48:42', '2012-09-30 23:48:42', 3, 1, NULL, 2, 'Test assignment for software tests 3', 3);
INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `authorId`, `comment`, `constantSetId`) VALUES (4, '2012-10-30 23:48:42', '2012-10-30 23:48:42', 1, 1, NULL, 2, 'Test assignment for software tests 4', 4);
INSERT INTO `assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `authorId`, `comment`, `constantSetId`) VALUES (5, '2012-10-30 23:48:43', '2012-10-30 23:48:43', 4, 1, NULL, 2, 'Test assignment for software tests 5', 5);

COMMIT;


-- -----------------------------------------------------
-- Data for table `columns`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'x', 1, 'double', 0, NULL);
INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'y', 1, 'double', 1, NULL);
INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'z', 1, 'double', 2, NULL);
INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'c1', 2, 'int', 0, NULL);
INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'c2', 2, 'int', 1, NULL);
INSERT INTO `columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (DEFAULT, DEFAULT, DEFAULT, 'c3', 2, 'int', 2, NULL);

COMMIT;


-- -----------------------------------------------------
-- Data for table `users`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `users` (`id`, `created`, `lastActionTime`, `name`, `password`, `roles`, `info`, `isDeleted`) VALUES (1, DEFAULT, DEFAULT, 'anonymous', NULL, '', 'User anonymous is a default user for CCDB. It has no modify privilegies', 0);
INSERT INTO `users` (`id`, `created`, `lastActionTime`, `name`, `password`, `roles`, `info`, `isDeleted`) VALUES (2, '2012-07-15 15:16:30', '2012-09-20 08:11:12', 'test_user', 'test', 'runrange_crate,runrange_delete', 'User for unit tests', 0);

COMMIT;


-- -----------------------------------------------------
-- Data for table `logs`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `logs` (`id`, `created`, `affectedIds`, `action`, `description`, `comment`, `authorId`) VALUES (1, DEFAULT, 'users_1', 'create', 'Created user \'anonymous\'', 'User anonymous is a default user for CCDB. It has no modify privilegies', 1);

COMMIT;


-- -----------------------------------------------------
-- Data for table `schemaVersions`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `schemaVersions` (`id`, `schemaVersion`) VALUES (1, 5);

COMMIT;

