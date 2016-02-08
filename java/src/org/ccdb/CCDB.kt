@file:JvmName("CCDB")
package org.jlab.ccdb


import org.jlab.ccdb.JDBCProvider
import org.jlab.ccdb.SQLiteProvider
import org.jlab.ccdb.MySqlProvider
import java.util.Date

/**
 * Creates CCDB data provider with connection string
 */
public fun createProvider(connectionStr: String): JDBCProvider {

    if (connectionStr.startsWith("sqlite://")) {

        //first lets check that sqlite string is right. The problem is that ccdb sticks to SqlAlchemy provider
        //where connection string for sqlite should start with sqlite:/// (three slashes)
        if (!connectionStr.startsWith("sqlite:///")) {
            throw IllegalArgumentException("Connection string for sqlite should start with 'sqlite:///' (3 slashes). " +
            "Provided connection string is'$connectionStr'")
        }
        return SQLiteProvider(connectionStr)
    }

    if (connectionStr.startsWith("mysql://")) {
        return MySqlProvider(connectionStr)
    }

    throw IllegalArgumentException("Can't open the connection string. Current version of CCDB Java opens only MySql " +
    "(should start with 'mysql://') and SQLite (should start with 'sqlite:///'). " +
    " Provided string: '$connectionStr'")
}

/**
 * Creates CCDB data provider with connection string and default run number
 */
public fun createProvider(connectionStr: String, run: Int): JDBCProvider {
    val provider = createProvider(connectionStr)
    provider.defaultRun = run
    return provider
}


/**
 * Creates CCDB data provider with connection string and default run number and default variation
 */
public fun createProvider(connectionStr: String, run: Int, variation: String): JDBCProvider {
    val provider = createProvider(connectionStr, run)
    provider.defaultVariation = variation
    return provider
}


/**
 * Creates CCDB data provider with connection string and default run number, variation and date
 */
public fun createProvider(connectionStr: String, run: Int, variation: String, date: Date): JDBCProvider {
    val provider = createProvider(connectionStr, run, variation)
    provider.defaultDate = date
    return provider
}