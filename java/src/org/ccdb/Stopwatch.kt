package org.jlab.ccdb

public class Stopwatch{

    private var startTime:Long = 0
    private var stopTime:Long = 0
    private var previousTime:Long = 0

    /** flag indicates the timer is running */
    public var isRunning:Boolean = false

    /** elapsed time in nanoseconds */
    public val elapsedTimeNano: Long
        get(){
        val elapsed =  if (isRunning) System.nanoTime() - startTime
        else stopTime - startTime
        return elapsed
    }

    //elapsed time in milliseconds
    public val elapsedTime: Double
        get(){
            return elapsedTimeNano / 1000000.0
        }

    public val elapsedTimeSec: Double
        get(){
            return elapsedTimeNano / 1000000000.0
        }

    public val totalTimeNano: Long
        get(){
            return previousTime + elapsedTimeNano
        }

    public val totalTime: Double
        get(){
            return totalTimeNano / 1000000.0
        }

    public val totalTimeSec: Double
        get(){
            return totalTimeNano / 1000000000.0
        }

    public fun start() {
        previousTime += elapsedTimeNano
        startTime = System.nanoTime()
        isRunning = true
    }

    public fun stop() {
        stopTime = System.nanoTime()
        isRunning = false
    }

    public fun clear(){
        previousTime = 0
        startTime = 0
        stopTime = 0
    }

    public override fun toString():String{
        return elapsedTime.toString()
    }
}