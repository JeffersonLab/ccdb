package org.ccdb

import java.util.HashMap
import org.ccdb.model.Directory
import java.util.Vector
import org.ccdb.model.Variation
import java.sql.Connection
import java.sql.PreparedStatement
import java.util.Date
import java.sql.DriverManager
import ccdb.helpers.combinePath
import java.sql.SQLException
import java.sql.ResultSet
import org.ccdb.model.TypeTable
import ccdb.helpers.extractDirectory
import ccdb.helpers.extractObjectname
import org.ccdb.model.TypeTableColumn
import org.ccdb.model.CellTypes
import org.ccdb.model.Assignment

public class CalibrationProvider{

    var directoriesByFullPath = HashMap<String,Directory>()
    var directoriesById = HashMap<Int, Directory>()
    var directories = Vector<Directory>()

    private var variationsById = HashMap<Int, Variation>()
    private var variationsByName = HashMap<String, Variation>()
    private var dirsAreLoaded = false;
    private var connection: Connection? = null
    private var prsSelectDirectories: PreparedStatement? = null
    private var prsSelectVariationById: PreparedStatement? = null
    private var prsSelectVariationByName: PreparedStatement? = null
    private var prsSelectData: PreparedStatement?=null
    private var prsSelectTable: PreparedStatement?=null
    private var prsSelectColumns: PreparedStatement?=null

    val rootDir = Directory(0, 0, "", Date(0), Date(0), "root directory"); {
        rootDir.fullPath = "/"
    }

    val isConnected:Boolean
        get(){
            return !(connection?.isClosed() ?: true)
        }

    fun connect(){
        val url = "jdbc:mysql://localhost:3306/ccdb"
        val user = "ccdb_user"
        val password = ""
        val name:String? = null

        connection = DriverManager.getConnection(url, user, password)
        val con:Connection = connection!!

        prsSelectDirectories = con.prepareStatement("SELECT id, parentId, name, created, modified, comment FROM directories");
        prsSelectVariationById = con.prepareStatement("SELECT id, parentId, name FROM variations WHERE id = ?")
        prsSelectVariationByName = con.prepareStatement("SELECT id, parentId, name FROM variations WHERE name = ?")
        //ok now we must build our mighty query...
        val dataQuery=
        "SELECT `assignments`.`id` AS `asId`, "+
        "`constantSets`.`vault` AS `blob`, "+
        "`assignments`.`modified` as `asModified`"+
        "FROM  `assignments` "+
        "USE INDEX (id_UNIQUE) "+
        "INNER JOIN `runRanges` ON `assignments`.`runRangeId`= `runRanges`.`id` "+
        "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "+
        "INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id` "+
        "WHERE  `runRanges`.`runMin` <= ? "+
        "AND `runRanges`.`runMax` >= ? "+
        "AND `assignments`.`variationId`= ? "+
        "AND `constantSets`.`constantTypeId` = ? "

        val timeConstrain = "AND UNIX_TIMESTAMP(`assignments`.`created`) <= ? "
        val orderBy = "ORDER BY `assignments`.`id` DESC LIMIT 1 "
        prsSelectData = con.prepareStatement(dataQuery + timeConstrain + orderBy)

        prsSelectTable = con.prepareStatement("SELECT `id`, UNIX_TIMESTAMP(`created`) as `created`, `name`, `directoryId`, `nRows`, `nColumns`, `comment` FROM `typeTables` WHERE `name` = ? AND `directoryId` = ?;")
        prsSelectColumns = con.prepareStatement("SELECT `id`, `name`, `columnType` FROM `columns` WHERE `typeId` = ? ORDER BY `order`;")

        dirsAreLoaded = false;

        //clear variations maps
        variationsById.clear();
        variationsByName.clear();
    }

    /** @brief Builds directory relational structure. Used right at the end of RetriveDirectories().
     *   this method is supposed to be called after new directories are loaded, but dont have hierarchical structure
     */
    fun buildDirectoryDependencies()
    {
        //clear the full path dictionary
        directoriesByFullPath.clear();
        directoriesByFullPath[rootDir.fullPath] = rootDir;

        //begin loop through the directories
        for(directory in directories){
            if(directory.parentId > 0){
                var parent = directoriesById[directory.parentId]
                if (parent == null) throw NullPointerException("Directory is not found in directoriesById HashMap")

                parent!!.addSubdirectory(directory)
            }
            else
            {
                // this directory  doesn't have parentId means it doesn't have parent
                // thus it lays in root directory so we place it to root directory
                rootDir.addSubdirectory(directory)
            }

            //creating full path for this directory
            val fullPath = combinePath(directory.parentDirectory?.fullPath ?: "", directory.name)
            directory.fullPath = fullPath

            //add to our full path map
            directoriesByFullPath[fullPath] = directory
        }
    }

    fun loadDirectories(){
        if (!isConnected) return

        try {
            val rs = prsSelectDirectories!!.executeQuery();

            //clear diretory arrays
            directories.clear();
            directoriesById.clear();

            //clear root directory (delete all directory structure objects)
            rootDir.disposeSubdirectories()
            rootDir.fullPath = "/";

            //loop through results
            while (rs.next()) {
                val created = rs.getDate("created")
                val modified = rs.getDate("modified")
                val directory = Directory(
                        rs.getInt("id"),
                        rs.getInt("parentId"),
                        rs.getString("name") ?: "NULL",
                        if (created != null) created else Date(0),
                        if (modified !=null) modified else Date(0),
                        rs.getString("comment")?: "")

                directories.add(directory)
                directoriesById[directory.id]= directory
            }
        }
        catch(e:SQLException ){
            throw e
        }
        finally {

        }

        buildDirectoryDependencies();
        dirsAreLoaded =true;
    }

    fun ensureDirsAreLoaded(){
        if(!dirsAreLoaded) loadDirectories()

    }

    fun getDirectory(fullPath: String): Directory{
        ensureDirsAreLoaded()
        val dir = directoriesByFullPath[fullPath]
        if(dir == null) throw SQLException("Directory with path '$fullPath' is not found in the database")
        return dir
    }

    fun getVariation(name: String):Variation{
        if(variationsByName.containsKey(name)) return variationsByName[name] as Variation

        //read variation from database
        prsSelectVariationByName!!.setString(1, name)
        val result = readVariationFromResultSet(prsSelectVariationByName!!.executeQuery())

        //Check we've got a variation
        if(result == null) throw SQLException("Variation with name='$name' is not found in the DB")
        return result
    }

    fun getVariation(id:Int):Variation{
        if(variationsById.containsKey(id)) return variationsById[id] as Variation

        //read variation from database
        prsSelectVariationById!!.setInt(1, id)
        val result = readVariationFromResultSet(prsSelectVariationById!!.executeQuery())

        //Check we've got a variation
        if(result == null) throw SQLException("Variation with name='$id' is not found in the DB")
        return result
    }

    private fun readVariationFromResultSet(rs:ResultSet):Variation?
    {
        //loop through results
        if (rs.next()) {
            val variation = Variation(
                    rs.getInt("id"),
                    rs.getInt("parentId"),
                    rs.getString("name") ?: "NULL")

            if(variation.parentId !=0 && variation.parentId != variation.id) {
                variation.setParent(getVariation(variation.parentId))
            }

            variationsById[variation.id] = variation
            variationsByName[variation.name] = variation
            return variation
        }

        return null
    }

    /** @brief Gets ConstantsType information from the DB
     *
     * @param  [in] fullPath  full path of the table
     * @return new TypeTable object
     */
    fun getTypeTable(fullPath:String):TypeTable{
        //get directory path and directory
        val dir = getDirectory(extractDirectory(fullPath))

        //retrieve name of our constant table
        val name = extractObjectname(fullPath)

        //get it from db etc...
        return getTypeTable(name, dir)
    }

    fun getTypeTable(name: String, parentDir: Directory):TypeTable
    {
        val prs = prsSelectTable!!
        prs.setString(1, name)
        prs.setInt(2, parentDir.id)
        val result = prs.executeQuery()
        //Check we've got a variation

        //loop through results
        if (result.next()) {
            val tableId = result.getInt("id")
            val tableName = result.getString("name")?:"NULL"
            val columns = loadColumns(tableId)

            val table = TypeTable(
                    tableId,
                    parentDir,
                    tableName,
                    columns
            )
            return table
        }
        else{
            throw SQLException("TypeTable with name='${combinePath(parentDir.fullPath, name)}' is not found in the DB")
        }
    }

    fun loadColumns(tableId: Int):Vector<TypeTableColumn>
    {
        val prs = prsSelectColumns!!
        prs.setInt(1, tableId)
        val result = prs.executeQuery()

        val columns = Vector<TypeTableColumn>()

        //Do we have anything
        var index = 0
        while (result.next()) {
            var cellType = when(result.getString("columnType")?:"NULL"){
                                "int" -> CellTypes.INT
                                "uint" -> CellTypes.UINT
                                "long" -> CellTypes.LONG
                                "ulong" -> CellTypes.ULONG
                                "double" -> CellTypes.DOUBLE
                                "string" -> CellTypes.STRING
                                "bool" -> CellTypes.BOOL
                                else -> CellTypes.DOUBLE
                            }
            val column = TypeTableColumn(
                    result.getInt("id"),
                    result.getString("name")?:"NULL",
                    index,
                    cellType
            )
            index++
            columns.add(column)
        }
        return columns
    }


    fun getAssignment(run:Int, table: TypeTable, time:Date, variation:Variation) :Assignment{

        val prs = prsSelectData!!
        "WHERE  `runRanges`.`runMin` <= ? "+
        "AND `runRanges`.`runMax` >= ? "+
        "AND `assignments`.`variationId`= ? "+
        "AND `constantSets`.`constantTypeId` = ? "
        prs.setInt(1, run)
        prs.setInt(2, run)
        prs.setInt(3, variation.id)
        prs.setInt(4, table.id)
        prs.setLong(5, time.getTime()/1000)
        val result = prs.executeQuery()

        if(!result.next()){
            //Ooppps! No data found!
            //Can we look the same request but in parent variation?
            val parVar = variation.parentVariation
            if (parVar !=null){
                return getAssignment(run, table, time, parVar)
            }
            else{
                throw SQLException("No data found for run='$run', table='${table.fullPath}', time<='$time'")
            }
        }

        //Data is found if we here
        val assgmt = Assignment(
                result.getInt("asId"),
                result.getString("blob")?:"",
                table,
                Date(result.getDate("asModified")?.getTime() ?: Date().getTime())
        )
        return assgmt

    }

}