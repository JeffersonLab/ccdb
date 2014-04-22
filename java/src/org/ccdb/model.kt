/**
 * Created by Dmitry on 3/24/2014.
 */


package org.jlab.ccdb

import java.util.Date
import java.util.Vector
import com.sun.javafx.scene.shape.PathUtils
import org.jlab.ccdb.helpers.combinePath
import java.util.HashMap

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
    fun addSubdirectory(subdirectory:Directory ){
        subdirectory.parentDirectory = this;
        subdirectories.add(subdirectory)

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

public class TypeTable(
        public val id:Int,
        public val directory:Directory,
        public val name:String,
        public val columns: Vector<TypeTableColumn>,
        public val rowsCount:Int)
{
    public val fullPath: String
        get(){
                return combinePath(directory.fullPath, name)
        }

    private var isDoneColumnsByName=false

    public val columnsByName: HashMap<String, TypeTableColumn> = HashMap<String, TypeTableColumn>()
        get(){
            if(!isDoneColumnsByName){
                for(column in columns) $columnsByName[column.name]=column
                isDoneColumnsByName = false
            }
            return $columnsByName
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
        val created:Date
){
    public val rowCount:Int get(){ return typeTable.rowsCount}

    public val columnCount:Int get(){return typeTable.columns.size}

    /**
     * gets data represented as number of columns
     */
    public val vectorString: Vector<String> = Vector<String>()
    get(){
        if($vectorString.empty){
            for (token in blob.split(dataSeparator)) $vectorString.add(token)
        }
        return $vectorString
    }


    /**
     * gets data represented as number of columns
     */
    public val tableString:Vector<Vector<String>> = Vector<Vector<String>>()
        get(){
            if($tableString.empty){
                val ncols = typeTable.columns.size
                val nrows = typeTable.rowsCount

                for(rowIndex in 0..nrows-1){
                    val row = Vector<String>()
                    for(colIndex in 0..ncols-1){
                        row.add(vectorString[rowIndex*ncols + colIndex])
                    }
                    $tableString.add(row)
                }
            }
            return $tableString
        }


    /**
     * gets data represented as number of columns
     */
    public val mapString: HashMap<String, String> = HashMap<String, String>()
        get(){
            if(mapString.empty) {
                val ncols = typeTable.columns.size

                for (colIndex in 0..ncols - 1) {
                    $mapString[typeTable.columns[colIndex].name] = vectorString[colIndex]
                }
            }
            return $mapString
        }

    public fun getColumnValuesString(columnName:String): Vector<String>{
        val column = typeTable.columnsByName[columnName]!!;
        return getColumnValuesString(column.index)
    }

    public fun getColumnValuesString(columnIndex:Int): Vector<String>{
        val result = Vector<String>()
        for(rowIndex in 0 .. rowCount - 1){
            result.add(vectorString[rowIndex*columnCount + columnIndex])
        }
        return result;
    }
}

/**
 *
 * types from 'int', 'uint', 'long', 'ulong', 'double', 'string', 'bool'
 */
public enum class CellTypes{
    BOOL
    INT
    UINT
    LONG
    ULONG
    DOUBLE
    STRING

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