/**
 * Created by Dmitry on 3/24/2014.
 */


package ccdb.model

import java.util.Date
import java.util.Vector

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

class TypeTable(
        val id:Int,
        val directoryId:Int,
        val name:String)
{
    var fullPath = ""

}
