SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL';

-- DROP SCHEMA IF EXISTS `clas12` ;
-- CREATE SCHEMA IF NOT EXISTS `clas12` DEFAULT CHARACTER SET latin1 ;
USE `clas12` ;

-- -----------------------------------------------------
-- Table `clas12`.`runRanges`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`runRanges` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`runRanges` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `name` VARCHAR(45) NULL DEFAULT '' ,
  `runMin` INT NOT NULL ,
  `runMax` INT NOT NULL ,
  `comment` TEXT NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `run search` (`runMin` ASC, `runMax` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `clas12`.`variations`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`variations` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`variations` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `name` VARCHAR(100) NOT NULL DEFAULT 'default' ,
  `description` VARCHAR(255) NULL ,
  `authorId` INT NULL DEFAULT 1 ,
  `comment` TEXT NULL DEFAULT NULL ,
  `parentId` INT NOT NULL DEFAULT 0 ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `name_search` USING HASH (`name` ASC) ,
  INDEX `fk_variations_variations1` (`parentId` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `clas12`.`directories`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`directories` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`directories` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `name` VARCHAR(255) NOT NULL DEFAULT '' ,
  `parentId` INT NOT NULL DEFAULT 0 ,
  `authorId` INT NULL DEFAULT 1 ,
  `comment` TEXT NULL DEFAULT NULL ,
  PRIMARY KEY (`id`) ,
  INDEX `fk_directories_directories1` (`parentId` ASC) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `clas12`.`typeTables`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`typeTables` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`typeTables` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `name` VARCHAR(255) NOT NULL ,
  `directoryId` INT NOT NULL ,
  `nRows` INT NOT NULL DEFAULT 1 ,
  `nColumns` INT NULL ,
  `nAssignments` INT NOT NULL DEFAULT 0 ,
  `authorId` INT NULL DEFAULT 1 ,
  `comments` TEXT NULL DEFAULT NULL ,
  PRIMARY KEY (`id`, `nRows`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `fk_constantTypes_directories1` (`directoryId` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `clas12`.`constantSets`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`constantSets` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`constantSets` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `vault` TEXT NOT NULL ,
  `constantTypeId` INT NOT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `fk_constantSets_constantTypes1` (`constantTypeId` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `clas12`.`eventRanges`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`eventRanges` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`eventRanges` (
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
-- Table `clas12`.`assignments`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`assignments` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`assignments` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `modified` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `variationId` INT NOT NULL ,
  `runRangeId` INT NULL ,
  `eventRangeId` INT NULL ,
  `constantSetId` INT NOT NULL ,
  `authorId` INT NULL DEFAULT 1 ,
  `comment` TEXT NULL ,
  PRIMARY KEY (`id`) ,
  INDEX `fk_assignments_variations1` (`variationId` ASC) ,
  INDEX `fk_assignments_runRanges1` (`runRangeId` ASC) ,
  INDEX `fk_assignments_constantSets1` (`constantSetId` ASC) ,
  INDEX `fk_assignments_eventRanges1` (`eventRangeId` ASC) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) ,
  INDEX `date_sort_index` USING BTREE (`created` DESC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `clas12`.`columns`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`columns` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`columns` (
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
  INDEX `fk_columns_constantTypes1` (`typeId` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `clas12`.`tags`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`tags` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`tags` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `name` VARCHAR(45) NOT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `clas12`.`variations_has_tags`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`variations_has_tags` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`variations_has_tags` (
  `variations_id` INT NOT NULL ,
  `tags_id` INT NOT NULL ,
  PRIMARY KEY (`variations_id`, `tags_id`) ,
  INDEX `fk_variations_has_tags_tags1` (`tags_id` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `clas12`.`authors`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`authors` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`authors` (
  `id` INT NOT NULL AUTO_INCREMENT ,
  `created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ,
  `lastActionTime` TIMESTAMP NOT NULL DEFAULT 20070101000000 ,
  `name` VARCHAR(100) NOT NULL ,
  PRIMARY KEY (`id`) ,
  UNIQUE INDEX `id_UNIQUE` (`id` ASC) )
ENGINE = MyISAM;


-- -----------------------------------------------------
-- Table `clas12`.`logs`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `clas12`.`logs` ;

CREATE  TABLE IF NOT EXISTS `clas12`.`logs` (
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



SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;

-- -----------------------------------------------------
-- Data for table `clas12`.`runRanges`
-- -----------------------------------------------------
START TRANSACTION;
USE `clas12`;
INSERT INTO `clas12`.`runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (1, NULL, NULL, 'all', 0, 2147483647, 'Default runrange that covers all runs');
INSERT INTO `clas12`.`runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (2, NULL, NULL, 'test', 500, 3000, 'Test runrange for software tests');
INSERT INTO `clas12`.`runRanges` (`id`, `created`, `modified`, `name`, `runMin`, `runMax`, `comment`) VALUES (3, NULL, NULL, '', 0, 2000, 'Test runrange. Secont test runrange for software test');

COMMIT;

-- -----------------------------------------------------
-- Data for table `clas12`.`variations`
-- -----------------------------------------------------
START TRANSACTION;
USE `clas12`;
INSERT INTO `clas12`.`variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`) VALUES (1, NULL, 'NULL', 'default', 'Default variation', NULL, 'Default variation', 0);
INSERT INTO `clas12`.`variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`) VALUES (2, NULL, 'NULL', 'mc', 'Mone-Carlo variations', NULL, 'Monte-Carlo specific variation', 0);
INSERT INTO `clas12`.`variations` (`id`, `created`, `modified`, `name`, `description`, `authorId`, `comment`, `parentId`) VALUES (3, NULL, 'NULL', 'test', 'Test variation', NULL, 'Variation for software test', 0);

COMMIT;

-- -----------------------------------------------------
-- Data for table `clas12`.`directories`
-- -----------------------------------------------------
START TRANSACTION;
USE `clas12`;
INSERT INTO `clas12`.`directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`) VALUES (1, NULL, NULL, 'test', 0, NULL, 'Soft test directory');
INSERT INTO `clas12`.`directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`) VALUES (2, NULL, NULL, 'subtest', 1, NULL, 'Soft test first subdirectory');
INSERT INTO `clas12`.`directories` (`id`, `created`, `modified`, `name`, `parentId`, `authorId`, `comment`) VALUES (3, NULL, NULL, 'test_vars', 1, NULL, NULL);

COMMIT;

-- -----------------------------------------------------
-- Data for table `clas12`.`typeTables`
-- -----------------------------------------------------
START TRANSACTION;
USE `clas12`;
INSERT INTO `clas12`.`typeTables` (`id`, `created`, `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `nAssignments`, `authorId`, `comments`) VALUES (1, NULL, NULL, 'test_table', 3, 2, 3, 2, NULL, 'Test type');
INSERT INTO `clas12`.`typeTables` (`id`, `created`, `modified`, `name`, `directoryId`, `nRows`, `nColumns`, `nAssignments`, `authorId`, `comments`) VALUES (2, NULL, NULL, 'test_table2', 3, 1, 3, 1, NULL, 'Test type 2');

COMMIT;

-- -----------------------------------------------------
-- Data for table `clas12`.`constantSets`
-- -----------------------------------------------------
START TRANSACTION;
USE `clas12`;
INSERT INTO `clas12`.`constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (1, NULL, NULL, '1.11|1.991211|10.002|2.001|2.9912|20.111', 1);
INSERT INTO `clas12`.`constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (2, NULL, NULL, '1.0|2.0|3.0|4.0|5.0|6.0', 1);
INSERT INTO `clas12`.`constantSets` (`id`, `created`, `modified`, `vault`, `constantTypeId`) VALUES (3, NULL, NULL, '1|2|3', 2);

COMMIT;

-- -----------------------------------------------------
-- Data for table `clas12`.`eventRanges`
-- -----------------------------------------------------
START TRANSACTION;
USE `clas12`;
INSERT INTO `clas12`.`eventRanges` (`id`, `created`, `modified`, `runNumber`, `eventMin`, `eventMax`, `comment`) VALUES (1, NULL, NULL, 1, 0, 1000, 'test');

COMMIT;

-- -----------------------------------------------------
-- Data for table `clas12`.`assignments`
-- -----------------------------------------------------
START TRANSACTION;
USE `clas12`;
INSERT INTO `clas12`.`assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `constantSetId`, `authorId`, `comment`) VALUES (1, NULL, NULL, 1, 1, NULL, 1, NULL, 'Test assignment for software tests');
INSERT INTO `clas12`.`assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `constantSetId`, `authorId`, `comment`) VALUES (2, NULL, NULL, 3, 2, NULL, 1, NULL, 'Test assignment for software tests 2');
INSERT INTO `clas12`.`assignments` (`id`, `created`, `modified`, `variationId`, `runRangeId`, `eventRangeId`, `constantSetId`, `authorId`, `comment`) VALUES (3, NULL, NULL, 2, 1, NULL, 2, NULL, 'Test assignment for software tests 3');

COMMIT;

-- -----------------------------------------------------
-- Data for table `clas12`.`columns`
-- -----------------------------------------------------
START TRANSACTION;
USE `clas12`;
INSERT INTO `clas12`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'x', 1, 'double', 0, NULL);
INSERT INTO `clas12`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'y', 1, 'double', 1, NULL);
INSERT INTO `clas12`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'z', 1, 'double', 2, NULL);
INSERT INTO `clas12`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'c1', 2, 'int', 0, NULL);
INSERT INTO `clas12`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'c2', 2, 'int', 1, NULL);
INSERT INTO `clas12`.`columns` (`id`, `created`, `modified`, `name`, `typeId`, `columnType`, `order`, `comment`) VALUES (NULL, NULL, NULL, 'c3', 2, 'int', 2, NULL);

COMMIT;

-- -----------------------------------------------------
-- Data for table `clas12`.`authors`
-- -----------------------------------------------------
START TRANSACTION;
USE `clas12`;
INSERT INTO `clas12`.`authors` (`id`, `created`, `lastActionTime`, `name`) VALUES (1, NULL, NULL, 'anonymous');

COMMIT;
