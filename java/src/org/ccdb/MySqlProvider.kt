package org.jlab.ccdb

import java.sql.DriverManager
import java.sql.Connection

class MySqlProvider(connectionString: String) : JDBCProvider(connectionString) {

    override fun connect() {
        // load the MySql-JDBC driver using the current class loader
        Class.forName("com.mysql.jdbc.Driver");

        //first check for uri type
        if (connectionString.indexOf("mysql://") != 0) {
            throw IllegalArgumentException("Connection string doesn't start with mysql:// but is given to MySqlProvider")
        }

        //ok we don't need mysql:// in the future. Moreover it will mess our separation logic
        var workStr = connectionString.substring(8)
        var userName = "ccdb_user"
        var password = ""

        //then if there is '@' that separates login/password part of uri
        val atPos = workStr.indexOf('@')

        if (atPos != -1) {
            var logPassStr: String
            when (atPos) {
                (workStr.length - 1) -> {
                    //it is like 'login:pwd@' string
                    logPassStr = workStr.substring(0, atPos)
                    workStr = ""
                }
                0 -> {
                    //it is like '@localhost' string
                    workStr = workStr.substring(1)
                    logPassStr = ""
                }
                else -> {
                    //a regular case
                    logPassStr = workStr.substring(0, atPos);
                    workStr = workStr.substring(atPos + 1);
                }
            }

            //is it only login or login&&password?
            var colonPos = logPassStr.indexOf(':');
            if (colonPos != -1) {
                userName = logPassStr.substring(0, colonPos)
                password = logPassStr.substring(colonPos + 1)
            } else {
                userName = logPassStr
            }
        }

        //ok, now we have only "address:port/database" part of the string
        //if we doesn't have /<database> we have to add it
        val host = "jdbc:mysql://" +
                if (workStr.indexOf('/') == -1) workStr + "/ccdb" else workStr

        //Connect to through JDBC
        connectJDBC(host, userName, password)
    }

    private fun connectJDBC(host: String, userName: String, password: String) {
        connection = DriverManager.getConnection(host, userName, password)

        val con: Connection = connection!!

        prsDirectories = con.prepareStatement("SELECT id, parentId, name, created, modified, comment FROM directories");
        prsVariationById = con.prepareStatement("SELECT id, parentId, name FROM variations WHERE id = ?")
        prsVariationByName = con.prepareStatement("SELECT id, parentId, name FROM variations WHERE name = ?")
        //ok now we must build our mighty query...
        val dataQuery =
                "SELECT `assignments`.`id` AS `asId`, " +
                        "`constantSets`.`vault` AS `blob`, " +
                        "`assignments`.`modified` as `asModified`" +
                        "FROM  `assignments` " +
                        "USE INDEX (id_UNIQUE) " +
                        "INNER JOIN `runRanges` ON `assignments`.`runRangeId`= `runRanges`.`id` " +
                        "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` " +
                        "INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id` " +
                        "WHERE  `runRanges`.`runMin` <= ? " +
                        "AND `runRanges`.`runMax` >= ? " +
                        "AND `assignments`.`variationId`= ? " +
                        "AND `constantSets`.`constantTypeId` = ? "

        val timeConstrain = "AND UNIX_TIMESTAMP(`assignments`.`created`) <= ? "
        val orderBy = "ORDER BY `assignments`.`id` DESC LIMIT 1 "
        prsData = con.prepareStatement(dataQuery + timeConstrain + orderBy)

        prsTable = con.prepareStatement("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` FROM `typeTables` WHERE `name` = ? AND `directoryId` = ?;")
        prsAllTables = con.prepareStatement("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` FROM `typeTables`")
        prsColumns = con.prepareStatement("SELECT `id`, `name`, `columnType` FROM `columns` WHERE `typeId` = ? ORDER BY `order`;")

        postConnect()
    }
}