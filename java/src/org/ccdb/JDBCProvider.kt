package org.jlab.ccdb

import java.util.HashMap
import java.util.Vector
import java.sql.Connection
import java.sql.PreparedStatement
import java.util.Date
import java.sql.SQLException
import java.sql.ResultSet

import org.jlab.ccdb.TypeTable
import org.jlab.ccdb.TypeTableColumn
import org.jlab.ccdb.CellTypes
import org.jlab.ccdb.Assignment
import org.jlab.ccdb.Variation
import org.jlab.ccdb.Directory
import org.jlab.ccdb.helpers.extractObjectname
import org.jlab.ccdb.helpers.extractDirectory
import org.jlab.ccdb.helpers.combinePath
import org.jlab.ccdb.helpers.parseRequest

open public class JDBCProvider(public val connectionString: String) {

    private var directoriesByFullPath = HashMap<String,Directory>()
    private var directoriesById = HashMap<Int, Directory>()
    private var directories = Vector<Directory>()
    private var variationsById = HashMap<Int, Variation>()
    private var variationsByName = HashMap<String, Variation>()
    private var dirsAreLoaded = false;

    protected var connection: Connection? = null
    protected var prsDirectories: PreparedStatement? = null
    protected var prsVariationById: PreparedStatement? = null
    protected var prsVariationByName: PreparedStatement? = null
    protected var prsData: PreparedStatement?=null
    protected var prsTable: PreparedStatement?=null
    protected var prsColumns: PreparedStatement?=null

    private var stopwatch = Stopwatch()

    private var cachedTypeTable: TypeTable? = null


    /**
     * Default run number which is used if no other run is defined
     */
    public var defaultRun:Int = 0


    /**
     * Default variation which is used if no variation specified in the request
     */
    public var defaultVariation:String = "default"


    /**
     * Default date which is used if no other date specified
     */
    public var defaultDate:Date = Date()


    /** returns root directory which is '/' in CCDB interpretation
     *
     * @remark this directory is not stored in database
     */
    public val rootDir: Directory = Directory(0, 0, "", Date(0), Date(0), "root directory"); {
        rootDir.fullPath = "/"
    }

    /**
     * Collect statistics of getData function
     */
    public var statisticsIsCollecting:Boolean = false

    /**
     * Gets statistics of getData function
     */
    public val statistics:RequestStatistics = RequestStatistics()


    /**
     * Flag indicating the connection to database is established
     */
    val isConnected:Boolean
        get(){
            return !(connection?.isClosed() ?: true)
        }


    /**
     * Connects to database using connection string
     */
    open public fun connect(){}


    /**
     * closes current connection
     */
    public fun close(){
        val con = connection
        if(con!=null) con.close()
    }


    /**
     * @warning (!) the function must be called after connect
     */
    protected open fun postConnect(){
        dirsAreLoaded = false

        //clear variations maps
        variationsById.clear()
        variationsByName.clear()

        //reset stopwatch
        stopwatch.clear()
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


    /**
     * Loads directories from database
     */
    fun loadDirectories(){
        if (!isConnected) return

        try {
            val rs = prsDirectories!!.executeQuery();

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


    /**
     * checks directories are loaded and loads directories if not
     */
    fun ensureDirsAreLoaded(){
        if(!dirsAreLoaded) loadDirectories()

    }


    /**
     *  Gets directory object by path
     */
    public fun getDirectory(fullPath: String): Directory{
        ensureDirsAreLoaded()
        val dir = directoriesByFullPath[fullPath]
        if(dir == null) throw SQLException("Directory with path '$fullPath' is not found in the database")
        return dir
    }


    /**
     * Gets variation by name
     */
    fun getVariation(name: String):Variation{
        if(variationsByName.containsKey(name)) return variationsByName[name] as Variation

        //read variation from database
        prsVariationByName!!.setString(1, name)
        val result = readVariationFromResultSet(prsVariationByName!!.executeQuery())

        //Check we've got a variation
        if(result == null) throw SQLException("Variation with name='$name' is not found in the DB")
        return result
    }


    /**
     *  gets variation by database ID
     */
    fun getVariation(id:Int):Variation{
        if(variationsById.containsKey(id)) return variationsById[id] as Variation

        //read variation from database
        prsVariationById!!.setInt(1, id)
        val result = readVariationFromResultSet(prsVariationById!!.executeQuery())

        //Check we've got a variation
        if(result == null) throw SQLException("Variation with name='$id' is not found in the DB")
        return result
    }


    /**
     * After result set with variation is selected by one of getVariation(*)
     * function, this function creates actual object and try recursively
     * to load a parent variation
     */
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
    public fun getTypeTable(fullPath:String):TypeTable{
        //get directory path and directory
        val dir = getDirectory(extractDirectory(fullPath))

        //retrieve name of our constant table
        val name = extractObjectname(fullPath)

        //get it from db etc...
        return getTypeTable(name, dir)
    }

    /**
     * Gets type table from db or returns null if no such table found in the DB
     */
    private fun getTypeTableUnsafe(name: String, parentDir: Directory):TypeTable?{
        val prs = prsTable!!
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
                    columns,
                    result.getInt("nRows")
            )
            return table
        }
        else{
            return null;
        }
    }


    /** @brief Gets ConstantsType information from the DB */
    fun getTypeTable(name: String, parentDir: Directory):TypeTable
    {
        //Maybe we already have the table cached?
        val cached = cachedTypeTable
        if(cached!=null && cached.name == name && parentDir == cached.directory) return cached

        //Read the table
        val table = getTypeTableUnsafe(name, parentDir)
        if(table == null) throw SQLException("TypeTable with name='${combinePath(parentDir.fullPath, name)}' is not found in the DB")
        cachedTypeTable = table
        return table
    }

    /** @brief Gets ConstantsType information from the DB
     *
     * @param  [in] fullPath  full path of the table
     * @return new TypeTable object
     */
    public fun isTypeTableAvailable(fullPath:String):Boolean{
        val dir = getDirectory(extractDirectory(fullPath))      // get directory path and directory
        val name = extractObjectname(fullPath)                  // retrieve name of our constant table
        return isTypeTableAvailable(name, dir)                  // get it from db etc...
    }

    /** @brief Gets ConstantsType information from the DB */
    fun isTypeTableAvailable(name: String, parentDir: Directory):Boolean
    {
        // The most common scenario is to check isTypeTableAvailable() first, then to call getTypeTable()
        // We cache TypeTable in isTypeTableAvailable, so getTypeTable() can use it
        cachedTypeTable = getTypeTableUnsafe(name, parentDir)
        return  if(cachedTypeTable != null) true else false
    }


    /**
     * Loads columns for the table
     */
    fun loadColumns(tableId: Int):Vector<TypeTableColumn>
    {
        val prs = prsColumns!!
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


    /**
     * Returns assignment object with is a class that holds CCDB data
     */
    fun getAssignment(run:Int, table: TypeTable, time:Date, variation:Variation) :Assignment{

        val prs = prsData!!
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
        val assignment = Assignment(
                            result.getInt("asId"),
                            result.getString("blob")?:"",
                            table,
                            Date(result.getDate("asModified")?.getTime() ?: Date().getTime()),
                            variation,
                            run)
        return assignment
    }

    /** Returns the Assignment objects which holds data values and infromation about them */
    public fun getData(request:String):Assignment{

        //Start statistics collection
        if(statisticsIsCollecting){
            stopwatch.start()
        }

        val parseResult = parseRequest(request)

        if(!parseResult.wasParsedPath){
            throw IllegalArgumentException("Request should be in from '<path>:<run>:<variation>:<date>', where " +
                                           "at least <path> should be provided. Original request is '$request'")
        }

        val table = getTypeTable(parseResult.path)

        //get variation?
        if(!parseResult.wasParsedVariation) parseResult.variation = defaultVariation
        val variation = getVariation(parseResult.variation)

        //got run?
        if(!parseResult.wasParsedRunNumber) parseResult.runNumber = defaultRun

        //got the date?
        if(!parseResult.wasParsedTime) parseResult.time = defaultDate

        //Date(0) means we have to use current time
        if(parseResult.time == Date(0)) parseResult.time = Date()

        //Read assignment from the database
        val assignment = getAssignment(parseResult.runNumber, table, parseResult.time, variation)

        //End statistics collection
        if(statisticsIsCollecting){
            stopwatch.stop()
            statistics.requests.add(parseResult)

            statistics.totalTime = stopwatch.totalTime
            statistics.lastRequestTime = stopwatch.elapsedTime

            //first time after connection takes longer. Separate it to another case
            if(statistics.requests.size == 1){
                statistics.firstTime = stopwatch.elapsedTime
            }
        }

        return assignment
    }

}