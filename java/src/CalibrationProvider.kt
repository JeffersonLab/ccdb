/**
 * Created by Dmitry on 3/24/2014.
 */

package ccdb.providers

import ccdb.model.Directory
import ccdb.helpers.combinePath
import java.util.Vector
import java.util.HashMap
import java.util.Date
import java.sql.DriverManager
import java.sql.Connection
import java.sql.PreparedStatement
import java.sql.SQLException
import ccdb.model.Variation
import java.sql.ResultSet


class CalibrationProvider{

    var directoriesByFullPath = HashMap<String,Directory>()
    var directoriesById = HashMap<Int, Directory>()
    var directories = Vector<Directory>()

    private var variationsById = HashMap<Int, Variation>()
    private var variationsByName = HashMap<String, Variation>()

    val rootDir = Directory(0, 0, "", Date(0), Date(0), "root directory"); {
        rootDir.fullPath = "/"
    }

    val isConnected:Boolean
        get(){

            return !(connection?.isClosed() ?: true)
            //if(connection == null) return false
            //else return connection.isClosed()
        }
    private var dirsAreLoaded = false;
    private var connection: Connection? = null
    private var prsSelectDirectories: PreparedStatement? = null
    private var prsSelectVariationById: PreparedStatement? = null
    private var prsSelectVariationByName: PreparedStatement? = null
    private var prsSelectDataNoTime: PreparedStatement?=null
    private var prsSelectDataByTime: PreparedStatement?=null

    fun connect(){
        val url = "jdbc:mysql://localhost:3306/ccdb"
        val user = "ccdb_user"
        val password = ""
        val name:String? = null

        connection = DriverManager.getConnection(url, user, password)
        prsSelectDirectories = connection!!.prepareStatement("SELECT id, parentId, name, created, modified, comment FROM directories");
        prsSelectVariationById = connection!!.prepareStatement("SELECT id, parentId, name FROM variations WHERE id = ?")
        prsSelectVariationByName = connection!!.prepareStatement("SELECT id, parentId, name FROM variations WHERE name = ?")
        //ok now we must build our mighty query...
        val dataQuery=
        "SELECT `assignments`.`id` AS `asId`, "+
        "`constantSets`.`vault` AS `blob` "+
        "FROM  `assignments` "+
        "USE INDEX (id_UNIQUE) "+
        "INNER JOIN `runRanges` ON `assignments`.`runRangeId`= `runRanges`.`id` "+
        "INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "+
        "INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id` "+
        "WHERE  `runRanges`.`runMin` <= ? "+
        "AND `runRanges`.`runMax` >= ? "+
        "AND `assignments`.`variationId`= ? "+
        "AND `constantSets`.`constantTypeId` = ? "
        
        val timeContrain = "AND UNIX_TIMESTAMP(`assignments`.`created`) <= ? "
        val orderBy = "ORDER BY `assignments`.`id` DESC LIMIT 1 "
        prsSelectDataNoTime = connection!!.prepareStatement(dataQuery + orderBy)
        prsSelectDataByTime = connection!!.prepareStatement(dataQuery + timeContrain + orderBy)


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
                println("${rs.getInt("id")} : ${rs.getString("name")}");
                val created = rs.getDate("created")
                val modified = rs.getDate("modified")
                val directory = Directory(
                        rs.getInt("id"),
                        rs.getInt("parentId"),
                        rs.getString("name") ?: "NULL",
                        if (created != null) created else Date(0),
                        if (modified!=null) modified else Date(0),
                        rs.getString("comment")?: "")

                directories.add(directory)
                directoriesById[directory.id]=directory
            }
        }
        catch(e:SQLException ){
            println(e.toString())
            throw e
        }
        finally {

        }

        buildDirectoryDependencies();
        dirsAreLoaded=true;
    }

    fun ensureDirsAreLoaded(){
        if(!dirsAreLoaded) loadDirectories()

    }

    fun getVariationByName(name: String):Variation{
        if(variationsByName.containsKey(name)) return variationsByName[name] as Variation

        //read variation from database
        prsSelectVariationByName!!.setString(1, name)
        val result = readVariationFromResultSet(prsSelectVariationByName!!.executeQuery())

        //Check we've got a variation
        if(result == null) throw SQLException("Variation with name='$name' is not found in the DB")
        return result
    }

    fun getVariationById(id:Int):Variation{
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
            println("${rs.getInt("id")} : ${rs.getString("name")}");

            val variation = Variation(
                    rs.getInt("id"),
                    rs.getInt("parentId"),
                    rs.getString("name") ?: "NULL")

            if(variation.parentId!=0 && variation.parentId != variation.id) {
                variation.setParent(getVariationById(variation.parentId))
            }

            variationsById[variation.id] = variation
            variationsByName[variation.name] = variation
            return variation
        }

        return null
    }
}

