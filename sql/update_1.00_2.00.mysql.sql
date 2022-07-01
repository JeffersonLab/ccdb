ALTER TABLE `variations`
ADD COLUMN `isLocked` TINYINT(1) NOT NULL DEFAULT 0 AFTER `parentId`,
ADD COLUMN `lockTime` TIMESTAMP NULL DEFAULT NULL AFTER `isLocked`,
ADD COLUMN `lockedByUserId` INT(11) NULL DEFAULT NULL AFTER `lockTime`,
ADD COLUMN `goBackBehavior` INT(11) NOT NULL DEFAULT 0 AFTER `lockedByUserId`,
ADD COLUMN `goBackTime` TIMESTAMP NULL DEFAULT NULL AFTER `goBackBehavior`,
ADD COLUMN `isDeprecated` TINYINT(1) NOT NULL DEFAULT 0 AFTER `goBackTime`,
ADD COLUMN `deprecatedByUserId` INT(11) NULL DEFAULT NULL AFTER `isDeprecated`;


ALTER TABLE `typeTables`
ADD COLUMN `isDeprecated` TINYINT(1) NOT NULL DEFAULT 0 AFTER `comment`,
ADD COLUMN `deprecatedByUserId` INT(11) NULL DEFAULT NULL AFTER `isDeprecated`,
ADD COLUMN `isLocked` TINYINT(1) NOT NULL DEFAULT 0 AFTER `deprecatedByUserId`,
ADD COLUMN `lockedByUserId` INT(11) NULL DEFAULT NULL AFTER `isLocked`,
ADD COLUMN `lockTime` TIMESTAMP NULL DEFAULT NULL AFTER `lockedByUserId`;


ALTER TABLE `directories`
ADD COLUMN `isDeprecated` TINYINT(1) NOT NULL DEFAULT 0 AFTER `comment`,
ADD COLUMN `deprecatedByUserId` INT(11) NULL DEFAULT NULL AFTER `isDeprecated`,
ADD COLUMN `isLocked` TINYINT(1) NOT NULL DEFAULT 0 AFTER `deprecatedByUserId`,
ADD COLUMN `lockedByUserId` INT(11) NULL DEFAULT NULL AFTER `isLocked`;

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
  PRIMARY KEY (`id`));


UPDATE `schemaVersions` SET schemaVersion = 5 WHERE `id` = 1;

