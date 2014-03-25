/**
 * Created by Dmitry on 3/24/2014.
 */
import java.sql.DriverManager
import ccdb.model.Directory
import java.util.Vector
import java.sql.Date
import ccdb.providers.CalibrationProvider

fun main(args: Array<String>) {
    val provider = CalibrationProvider()
    provider.connect()
    provider.loadDirectories()

    val variation = provider.getVariationByName("moc")
    println("variation '${variation.name}' is child of '${variation.parentVariation?.name}'")

    print("Hello")
}