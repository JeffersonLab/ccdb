package kotlinExamples

import org.jlab.ccdb.JDBCProvider
import org.jlab.ccdb.MySqlProvider
import org.jlab.ccdb.SQLiteProvider
import org.jlab.ccdb.Stopwatch
import java.text.SimpleDateFormat
import java.util.*


fun testSQLite(){

    val ccdbHome = System.getenv("CCDB_HOME")
    if(ccdbHome == null){
        println("\$CCDB_HOME is not set")
        return
    }
    println("------------ SQLITE ---------------")
    val provider = SQLiteProvider("sqlite:///$ccdbHome/sql/ccdb.sqlite")
    provider.connect()
    val sw = Stopwatch()
    sw.start()
    val variation = provider.getVariation("default")
    val table = provider.getTypeTable("/test/test_vars/test_table")
    var asgmt1 = provider.getAssignment(0, table, Date(), variation)

    sw.stop()
    println("time for request is $sw")

    println("Data is '${asgmt1.blob}'")
    println("table full path: '${table.fullPath}' columns are: ")
    for (column in table.columns){
        println("    name: '${column.name}'   type:'${column.cellType}'")
    }

}

fun main(args: Array<String>) {
    val provider = MySqlProvider("mysql://localhost")
    provider.connect()
    provider.loadDirectories()

    val sw = Stopwatch()
    sw.start()
    val variation = provider.getVariation("default")
    val table = provider.getTypeTable("/test/test_vars/test_table")
    var asgmt1 = provider.getAssignment(0, table, Date(), variation)

    sw.stop()
    println("time for request is $sw")

    println("Data is '${asgmt1.blob}'")
    println("table full path: '${table.fullPath}' columns are: ")
    for (column in table.columns){
        println("    name: '${column.name}'   type:'${column.cellType}'")
    }
    println("variation '${variation.name}' is child of '${variation.parentVariation?.name}'")

    val formatter = SimpleDateFormat("yyyy-MM-dd hh:mm:ss")
    val parsedDate = formatter.parse("2012-08-30 23:48:42")?:Date()
    sw.start()
    val asgmt2 = provider.getAssignment(1000, table, parsedDate, provider.getVariation("test"))
    sw.stop()
    println("time for request2 is $sw")

    println("asgmt2 values: ")
    for (value in asgmt2.vectorString){
        println("   $value")
    }

    println("asgmt2 values as table: ")
    for (row in asgmt2.tableString){
        for(cell in row){
            print(" $cell ")
        }
        println()
    }


    println("Data is '${asgmt2.blob}'")


    getAllDirectories(provider)     // Example of how to show directories

    testSQLite()                    // Test of SQLite DB
}


/// Example of how to show directories
fun getAllDirectories(provider: JDBCProvider){
    // function loads directories if they hasn't been loaded yet (and in this scenario they hasn't been)
    provider.ensureDirsAreLoaded()

    // 'root' directory is '/' (it is not stored database)
    val root = provider.rootDir

    // iterate over directories
    for (dir in root.subdirectories) {
        println(dir.fullPath)
        for (subDir in dir.subdirectories) {
            println("      " + subDir.fullPath)
        }
    }
}