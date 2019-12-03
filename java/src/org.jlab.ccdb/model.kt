/**
 * Created by Dmitry on 3/24/2014.
 */


package org.jlab.ccdb

import java.util.Date
import java.util.Vector
import java.util.HashMap
import org.jlab.ccdb.helpers.combinePath
import kotlin.text.toBoolean


val dataSeparator = '|'

class Directory(
        val id:Int,             /// DB id
        val parentId:Int,       /// DB id of parent directory. Id=0 - root directory
        val name:String,        /// Name of the directory
        val createdTime:Date,   /// Creation time
        val modifiedTime:Date,  /// Last modification time
        val comment:String      /// Full description of the directory
        ){

    var parentDirectory:Directory?=null     /// null if there is no parent directory
    var fullPath = ""                       /// Full path (including self name) of the directory


    var subdirectories = Vector<Directory>()


    /**
     * @brief Adds a subdirectory of this directory
     *
     * Adds a subdirectory of this directory
     * Automatically adds "this" as mParent for child
     *
     * @param subDirectory Child directory to be added
     */
    fun addSubdirectory(subDirectory:Directory ){
        subDirectory.parentDirectory = this;
        subdirectories.add(subDirectory)

    }

    /**
     * @brief deletes all subdirectories recursively
     */
    fun disposeSubdirectories(){
        //TODO do we need it with garbage collector???
        if (subdirectories.size >0 ){
            for(subdirectory in subdirectories){
                subdirectory.disposeSubdirectories()
            }
            subdirectories.clear()
        }
    }
}


class Variation(
        val id:Int,
        val parentId:Int,
        val name:String){

    var parentVariation:Variation? = null
    var children = Vector<Variation>()

    fun setParent(parent:Variation){
        this.parentVariation = parent
        parent.children.add(this)
    }
}

class TypeTable(
        val id:Int,
        val directory:Directory,
        val name:String,
        val columns: Vector<TypeTableColumn>,
        val rowsCount:Int)
{
    val fullPath: String
        get(){
                return combinePath(directory.fullPath, name)
        }

    private var isDoneColumnsByName=false

    public val _columnsByName: HashMap<String, TypeTableColumn> = HashMap<String, TypeTableColumn>()
    public val columnsByName: HashMap<String, TypeTableColumn>
        get(){
            if(!isDoneColumnsByName){
                for(column in columns) _columnsByName[column.name]=column
                isDoneColumnsByName = false
            }
            return _columnsByName
        }
}

class TypeTableColumn(
        val id:Int,
        val name:String,
        val index:Int,
        val cellType:CellTypes)


/**
 * Class that represents CCDB data set
 */
class Assignment(
        val id:Int,
        val blob:String,
        val typeTable:TypeTable,
        val created:Date,
        val variation:Variation,
        val run:Int
){
    /**
     * Gets number of rows
     */
    val rowCount:Int get(){ return typeTable.rowsCount}


    /**
     * Gets number of columns
     */
    val columnCount:Int get(){return typeTable.columns.size}

    /**
     * Gets data represented as one vector of string values
     */
    private  val _vectorString: Vector<String> = Vector<String>()
    public val vectorString: Vector<String>
    get(){
        if(_vectorString.isEmpty()){
            for (token in blob.split(dataSeparator)) _vectorString.add(token)
        }
        return _vectorString
    }

    /**
     * Gets data represented as one vector of int values
     */
    public val vectorInt: Vector<Int> by lazy {
        val result = Vector<Int>()
        blob.split(dataSeparator).mapTo(result) { it.toInt() }
        result
    }

    /**
     * Gets data represented as one vector of int values
     */
    public val vectorLong: Vector<Long> by lazy {
        val result = Vector<Long>()
        blob.split(dataSeparator).mapTo(result) { it.toLong() }
        result
    }

    /**
     * Gets data represented as one vector of int values
     */
    public val vectorDouble: Vector<Double> by lazy {
        val result = Vector<Double>()
        for (token in blob.split(dataSeparator)) result.add(token.toDouble())
        result
    }

    /**
     * Gets data represented as one vector of boolean values
     */
    public val vectorBoolean: Vector<Boolean> by lazy {
        val result = Vector<Boolean>()
        blob.split(dataSeparator).mapTo(result) { it.toBoolean() }
        result
    }


    /**
     * Gets data represented as row-wise table
     */
    private val _tableString = Vector<Vector<String>>()
    public val tableString:Vector<Vector<String>>
        get(){
            if(_tableString.isEmpty()){
                val ncols = typeTable.columns.size
                val nrows = typeTable.rowsCount

                for(rowIndex in 0 until nrows){
                    val row = Vector<String>()
                    for(colIndex in 0..ncols-1){
                        row.add(vectorString[rowIndex*ncols + colIndex])
                    }
                    _tableString.add(row)
                }
            }
            return _tableString
        }

    /**
     * Gets data represented as row-wise table of Integers
     */
    public val tableInt:Vector<Vector<Int>> by lazy {
        val result = Vector<Vector<Int>>()
        for(row in tableString){
            val parsedRow = Vector<Int>()
            for(cell in row){
                parsedRow.add(cell.toInt())
            }
            result.add(parsedRow)
        }
        result
    }

    /**
     * Gets data represented as row-wise table of Longs
     */
    public val tableLong:Vector<Vector<Long>> by lazy {
        val result = Vector<Vector<Long>>()
        for(row in tableString){
            val parsedRow = Vector<Long>()
            for(cell in row){
                parsedRow.add(cell.toLong())
            }
            result.add(parsedRow)
        }
        result
    }

    /**
     * Gets data represented as row-wise table of Doubles
     */
    public val tableDouble:Vector<Vector<Double>> by lazy {
        val result = Vector<Vector<Double>>()
        for(row in tableString){
            val parsedRow = Vector<Double>()
            for(cell in row){
                parsedRow.add(cell.toDouble())
            }
            result.add(parsedRow)
        }
        result
    }

    /**
     * Gets data represented as row-wise table of Booleans
     */
    public val tableBoolean:Vector<Vector<Boolean>> by lazy {
        val result = Vector<Vector<Boolean>>()
        for(row in tableString){
            val parsedRow = Vector<Boolean>()
            for(cell in row){
                parsedRow.add(cell.toBoolean())
            }
            result.add(parsedRow)
        }
        result
    }


    /**
     * gets data represented as map of {column name: data}
     */
    private val _mapString = HashMap<String, String>()
    public val mapString: HashMap<String, String>
        get(){
            if(_mapString.isEmpty()) {
                val ncols = typeTable.columns.size

                for (colIndex in 0..ncols - 1) {
                    _mapString[typeTable.columns[colIndex].name] = vectorString[colIndex]
                }
            }
            return _mapString
        }

    /**
     * Gets all values in one column by column name
     */
    fun getColumnValuesString(columnName:String): Vector<String>{
        val column = typeTable.columnsByName[columnName]!!;
        return getColumnValuesString(column.index)
    }

    /**
     * Gets all values in one column by column name
     */
    fun getColumnValuesInt(columnName:String): Vector<Int>{
        val column = typeTable.columnsByName[columnName]!!;
        return getColumnValuesInt(column.index)
    }

    /**
     * Gets all values in one column by column name
     */
    fun getColumnValuesLong(columnName:String): Vector<Long>{
        val column = typeTable.columnsByName[columnName]!!;
        return getColumnValuesLong(column.index)
    }

    /**
     * Gets all values in one column by column name
     */
    fun getColumnValuesDouble(columnName:String): Vector<Double>{
        val column = typeTable.columnsByName[columnName]!!;
        return getColumnValuesDouble(column.index)
    }

    /**
     * Gets all values in one column by column name
     */
    fun getColumnValuesBoolean(columnName:String): Vector<Boolean>{
        val column = typeTable.columnsByName[columnName]!!;
        return getColumnValuesBoolean(column.index)
    }

    /**
     * Gets all values in one column by column index
     */
    private fun getColumnValuesString(columnIndex:Int): Vector<String>{
        val result = Vector<String>()
        (0 until rowCount).mapTo(result) { vectorString[it *columnCount + columnIndex] }
        return result;
    }

    /**
     * Gets all values as Int in one column by column index
     */
    private fun getColumnValuesInt(columnIndex:Int): Vector<Int>{
        val result = Vector<Int>()
        val values = getColumnValuesString(columnIndex)
        values.mapTo(result) { it.toInt() }
        return result;
    }

    /**
     * Gets all values as Double in one column by column index
     */
    fun getColumnValuesDouble(columnIndex:Int): Vector<Double>{
        val result = Vector<Double>()
        val values = getColumnValuesString(columnIndex)
        values.mapTo(result) { it.toDouble() }
        return result;
    }

    /**
     * Gets all values as Long in one column by column index
     */
    private fun getColumnValuesLong(columnIndex:Int): Vector<Long>{
        val result = Vector<Long>()
        val values = getColumnValuesString(columnIndex)
        for(value in values){
            result.add(value.toLong())
        }
        return result;
    }

    /**
     * Gets all values as Boolean in one column by column index
     */
    private fun getColumnValuesBoolean(columnIndex:Int): Vector<Boolean>{
        val result = Vector<Boolean>()
        val values = getColumnValuesString(columnIndex)
        for(value in values){
            result.add(value.toBoolean())
        }
        return result;
    }

}

/**
 *
 * types from 'int', 'uint', 'long', 'ulong', 'double', 'string', 'bool'
 */
public enum class CellTypes{
    BOOL,
    INT,
    UINT,
    LONG,
    ULONG,
    DOUBLE,
    STRING;

    override fun toString():String{
        return when(this){
            INT -> "int"
            UINT -> "uint"
            LONG -> "long"
            ULONG -> "ulong"
            DOUBLE -> "double"
            STRING -> "string"
            BOOL -> "bool"
        }
    }
}