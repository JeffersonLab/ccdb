 
SELECT  `assignments`.`id` AS `asId`, 
        `constantSets`.`vault` AS `blob` 
        FROM  `assignments` 
        USE INDEX (id_UNIQUE)
        INNER JOIN `runRanges` ON `assignments`.`runRangeId`= `runRanges`.`id` 
        /*INNER JOIN `variations` ON `assignments`.`variationId`= `variations`.`id` */
        INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` 
        WHERE  `runRanges`.`runMin` <= '100' 
        AND `runRanges`.`runMax` >= '100'
        AND `assignments`.`variationId` = 1
        AND `constantSets`.`constantTypeId` ='1' 
        ORDER BY `assignments`.`id` DESC 
        LIMIT 1 ;
