SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

DROP SCHEMA IF EXISTS `ccdb` ;
CREATE SCHEMA IF NOT EXISTS `ccdb` DEFAULT CHARACTER SET latin1 ;
USE `ccdb` ;

-- -----------------------------------------------------
-- Table `ccdb`.`runRanges`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`runRanges` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`runRanges` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `modified` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `name` VARCHAR(45) NULL DEFAULT '' ,
  `runMin` INT NOT NULL ,
  `runMax` INT NOT NULL ,
  `comment` TEXT NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `run search` (`runMin` ASC, `runMax` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`variations`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`variations` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`variations` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `modified` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `name` VARCHAR(100) NOT NULL DEFAULT 'default' ,
  `description` VARCHAR(255) NULL ,
  `authorId` INT NULL DEFAULT 1 ,
  `comment` TEXT NULL DEFAULT NULL ,
  `parentId` INT NOT NULL DEFAULT 0 ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `name_search` USING HASH (`name` ASC) ,
  INDEX `fk_variations_variations1_idx` (`parentId` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`directories`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`directories` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`directories` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `name` VARCHAR(255) NOT NULL DEFAULT '' ,
  `parentId` INT NOT NULL DEFAULT 0 ,
  `authorId` INT NULL DEFAULT 1 ,
  `comment` TEXT NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) ,
  INDEX `fk_directories_directories1_idx` (`parentId` ASC) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`typeTables`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`typeTables` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`typeTables` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `name` VARCHAR(255) NOT NULL ,
  `directoryId` INT NOT NULL ,
  `nRows` INT NOT NULL DEFAULT 1 ,
  `nColumns` INT NOT NULL ,
  `nAssignments` INT NOT NULL DEFAULT 0 ,
  `authorId` INT NULL DEFAULT 1 ,
  `comments` TEXT NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `fk_constantTypes_directories1_idx` (`directoryId` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`constantSets`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`constantSets` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`constantSets` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `vault` TEXT NOT NULL ,
  `constantTypeId` INT NOT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `fk_constantSets_constantTypes1_idx` (`constantTypeId` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`eventRanges`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`eventRanges` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`eventRanges` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `runNumber` INT NOT NULL ,
  `eventMin` INT NOT NULL ,
  `eventMax` INT NOT NULL ,
  `comment` TEXT NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `ideventRanges_UNIQUE` (`id` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`assignments`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`assignments` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`assignments` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NULL DEFAULT 20070101000000 ,
  `variationId` INT NOT NULL ,
  `runRangeId` INT NULL ,
  `eventRangeId` INT NULL ,
  `constantSetId` INT NOT NULL ,
  `authorId` INT NULL DEFAULT 1 ,
  `comment` TEXT NULL ,
  PRIMARY KEY (`id`) ,
  INDEX `fk_assignments_variations1_idx` (`variationId` ASC) ,
  INDEX `fk_assignments_runRanges1_idx` (`runRangeId` ASC) ,
  INDEX `fk_assignments_constantSets1_idx` (`constantSetId` ASC) ,
  INDEX `fk_assignments_eventRanges1_idx` (`eventRangeId` ASC) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `date_sort_index` USING BTREE (`created` DESC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`columns`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`columns` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`columns` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `name` VARCHAR(45) NOT NULL ,
  `typeId` INT NOT NULL ,
  `columnType` ENUM('int', 'uint','long','ulong','double','string','bool') NULL ,
  `order` INT NOT NULL ,
  `comment` TEXT NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `fk_columns_constantTypes1_idx` (`typeId` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`tags`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`tags` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`tags` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `name` VARCHAR(45) NOT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`variations_has_tags`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`variations_has_tags` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`variations_has_tags` (
  `variations_id` INT NOT NULL ,
  `tags_id` INT NOT NULL ,
  PRIMARY KEY (`variations_id`, `tags_id`) ,
  INDEX `fk_variations_has_tags_tags1_idx` (`tags_id` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`authors`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`authors` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`authors` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `lastActionTime` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `name` VARCHAR(100) NOT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`logs`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`logs` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`logs` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `affectedTables` TEXT NULL ,
  `affectedIds` VARCHAR(100) NOT NULL ,
  `description` VARCHAR(255) NULL ,
  `authorId` INT NOT NULL ,
  `fullDescription` TEXT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `ccdb`.`schemaVersions`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `ccdb`.`schemaVersions` ;

CREATE  TABLE IF NOT EXISTS `ccdb`.`schemaVersions` (
  `id` INT NOT NULL ,
  `schemaVersion` INT NULL DEFAULT 1 ,
  PRIMARY KEY (`id`) )
ENGINE = InnoDB;



SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;

-- -----------------------------------------------------
-- Data for table `ccdb`.`runRanges`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `ccdb`.`runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (1, NULL, NULL, 'all', 0, 2147483647, 'Default runrange that covers all runs');
INSERT INTO `ccdb`.`runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (2, NULL, NULL, 'test', 500, 3000, 'Test runrange for software tests');
INSERT INTO `ccdb`.`runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (3, NULL, NULL, '', 0, 2000, 'Test runrange. Secont test runrange for software test');

COMMIT;

-- -----------------------------------------------------
-- Data for table `ccdb`.`variations`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `ccdb`.`variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`) VALUES (1, NULL, NULL, 'default', 'Default variation', NULL, 'Default variation', 0);
INSERT INTO `ccdb`.`variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`) VALUES (2, NULL, NULL, 'mc', 'Mone-Carlo variations', NULL, 'Monte-Carlo specific variation', 0);
INSERT INTO `ccdb`.`variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`) VALUES (3, NULL, NULL, 'test', 'Test variation', NULL, 'Variation for software test', 0);

COMMIT;

-- -----------------------------------------------------
-- Data for table `ccdb`.`directories`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `ccdb`.`directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`) VALUES (1, NULL, NULL, 'test', 0, NULL, 'Soft test directory');
INSERT INTO `ccdb`.`directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`) VALUES (2, NULL, NULL, 'subtest', 1, NULL, 'Soft test first subdirectory');
INSERT INTO `ccdb`.`directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`) VALUES (3, NULL, NULL, 'test_vars', 1, NULL, NULL);

COMMIT;

-- -----------------------------------------------------
-- Data for table `ccdb`.`typeTables`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `ccdb`.`typeTables` (`id`, `created`, `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `nAssignments`, `authorId`, `comments`) VALUES (1, NULL, NULL, 'test_table', 3, 2, 3, 2, NULL, 'Test type');
INSERT INTO `ccdb`.`typeTables` (`id`, `created`, `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `nAssignments`, `authorId`, `comments`) VALUES (2, NULL, NULL, 'test_table2', 3, 1, 3, 1, NULL, 'Test type 2');

COMMIT;

-- -----------------------------------------------------
-- Data for table `ccdb`.`constantSets`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `ccdb`.`constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (1, '2012-07-30 23:48:42', '2012-07-30 23:48:42', '1.11|1.991211|10.002|2.001|2.9912|20.111', 1);
INSERT INTO `ccdb`.`constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (2, '2012-08-30 23:48:42', '2012-08-30 23:48:42', '1.0|2.0|3.0|4.0|5.0|6.0', 1);
INSERT INTO `ccdb`.`constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (3, '2012-09-30 23:48:42', '2012-09-30 23:48:42', '10|20|30', 2);
INSERT INTO `ccdb`.`constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (4, '2012-10-30 23:48:42', '2012-10-30 23:48:42', '2.2|2.3|2.4|2.5|2.6|2.7', 1);

COMMIT;

-- -----------------------------------------------------
-- Data for table `ccdb`.`eventRanges`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `ccdb`.`eventRanges` (`id`, `created`, `modified`, `runNumber`, `eventMin`, `eventMax`, `comment`) VALUES (1, NULL, NULL, 1, 0, 1000, 'test');

COMMIT;

-- -----------------------------------------------------
-- Data for table `ccdb`.`assignments`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `ccdb`.`assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `constantSetId`, `authorId`, `comment`) VALUES (1, '2012-07-30 23:48:42', '2012-07-30 23:48:42', 1, 1, NULL, 1, NULL, 'Test assignment for software tests');
INSERT INTO `ccdb`.`assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `constantSetId`, `authorId`, `comment`) VALUES (2, '2012-08-30 23:48:42', '2012-08-30 23:48:42', 3, 2, NULL, 2, NULL, 'Test assignment for software tests 2');
INSERT INTO `ccdb`.`assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `constantSetId`, `authorId`, `comment`) VALUES (3, '2012-09-30 23:48:42', '2012-09-30 23:48:42', 2, 1, NULL, 3, NULL, 'Test assignment for software tests 3');
INSERT INTO `ccdb`.`assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `constantSetId`, `authorId`, `comment`) VALUES (4, '2012-10-30 23:48:42', '2012-10-30 23:48:42', 1, 1, NULL, 4, NULL, 'Test assignment for software tests');

COMMIT;

-- -----------------------------------------------------
-- Data for table `ccdb`.`columns`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `ccdb`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'x', 1, 'double', 0, NULL);
INSERT INTO `ccdb`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'y', 1, 'double', 1, NULL);
INSERT INTO `ccdb`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'z', 1, 'double', 2, NULL);
INSERT INTO `ccdb`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'c1', 2, 'int', 0, NULL);
INSERT INTO `ccdb`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'c2', 2, 'int', 1, NULL);
INSERT INTO `ccdb`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'c3', 2, 'int', 2, NULL);

COMMIT;

-- -----------------------------------------------------
-- Data for table `ccdb`.`authors`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `ccdb`.`authors` (`id`, `created`, `lastActionTime`, `name`) VALUES (1, NULL, NULL, 'anonymous');

COMMIT;

-- -----------------------------------------------------
-- Data for table `ccdb`.`schemaVersions`
-- -----------------------------------------------------
START TRANSACTION;
USE `ccdb`;
INSERT INTO `ccdb`.`schemaVersions` (`id`, `schemaVersion`) VALUES (1, 2);

COMMIT;
