SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL';

ALTER TABLE `variations`
    ADD COLUMN `isLocked` TINYINT(1) NOT NULL DEFAULT 0 AFTER `parentId`,
    ADD COLUMN `lockTime` TIMESTAMP NULL DEFAULT NULL AFTER `isLocked`,
    ADD COLUMN `lockAuthorId` VARCHAR(45) NULL DEFAULT NULL AFTER `lockTime`,
    ADD COLUMN `goBackBehavior` INT(11) NOT NULL DEFAULT 0 AFTER `lockAuthorId`,
    ADD COLUMN `goBackTime` TIMESTAMP NULL DEFAULT NULL AFTER `goBackBehavior`;


ALTER TABLE `typeTables` 
    ADD COLUMN `isDeprecated` TINYINT(1) NOT NULL DEFAULT 0 AFTER `comment`,
    ADD COLUMN `deprecatedById` INT(11) NOT NULL DEFAULT -1 AFTER `isDeprecated`,
    ADD COLUMN `isLocked` TINYINT(1) NOT NULL DEFAULT 0 AFTER `deprecatedById`,
    ADD COLUMN `lockAuthorId` INT(11) NULL DEFAULT NULL AFTER `isLocked`,
    ADD COLUMN `lockTime` TIMESTAMP NULL DEFAULT NULL AFTER `lockAuthorId`;

ALTER TABLE `directories`
    ADD COLUMN `isDeprecated` TINYINT(1) NOT NULL DEFAULT 0 AFTER `comment`,
    ADD COLUMN `deprecatedById` INT(11) NOT NULL DEFAULT -1 AFTER `isDeprecated`;


CREATE TABLE IF NOT EXISTS `assignmentsMaterializedView` (
  `id` INT(11) NOT NULL AUTO_INCREMENT,
  `assignmentsId` INT(11) NOT NULL,
  `variationsId` INT(11) NOT NULL,
  `constantSetsId` INT(11) NOT NULL,
  `typeTablesId` INT(11) NOT NULL,
  `runRangesId` INT(11) NOT NULL,
  `runMin` INT(11) NOT NULL,
  `runMax` INT(11) NOT NULL,
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
ENGINE = InnoDB
DEFAULT CHARACTER SET = latin1;

UPDATE `schemaVersions` SET schemaVersion = 5 WHERE `id` = 1;

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;
