ALTER TABLE `variations`
ADD COLUMN `isLocked` TINYINT NOT NULL DEFAULT 0 AFTER `parentId`,
ADD COLUMN `lockTime` TIMESTAMP NULL DEFAULT NULL AFTER `isLocked`,
ADD COLUMN `lockedByUserId` INT NULL DEFAULT NULL AFTER `lockTime`,
ADD COLUMN `goBackBehavior` INT NOT NULL DEFAULT 0 AFTER `lockedByUserId`,
ADD COLUMN `goBackTime` TIMESTAMP NULL DEFAULT NULL AFTER `goBackBehavior`,
ADD COLUMN `isDeprecated` TINYINT NOT NULL DEFAULT 0 AFTER `goBackTime`,
ADD COLUMN `deprecatedByUserId` INT NULL DEFAULT NULL AFTER `isDeprecated`;


ALTER TABLE `typeTables`
ADD COLUMN `isDeprecated` TINYINT NOT NULL DEFAULT 0 AFTER `comment`,
ADD COLUMN `deprecatedByUserId` INT NULL DEFAULT NULL AFTER `isDeprecated`,
ADD COLUMN `isLocked` TINYINT NOT NULL DEFAULT 0 AFTER `deprecatedByUserId`,
ADD COLUMN `lockedByUserId` INT NULL DEFAULT NULL AFTER `isLocked`,
ADD COLUMN `lockTime` TIMESTAMP NULL DEFAULT NULL AFTER `lockedByUserId`;


ALTER TABLE `directories`
ADD COLUMN `isDeprecated` TINYINT NOT NULL DEFAULT 0 AFTER `comment`,
ADD COLUMN `deprecatedByUserId` INT NULL DEFAULT NULL AFTER `isDeprecated`,
ADD COLUMN `isLocked` TINYINT NOT NULL DEFAULT 0 AFTER `deprecatedByUserId`,
ADD COLUMN `lockedByUserId` INT NULL DEFAULT NULL AFTER `isLocked`;

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



