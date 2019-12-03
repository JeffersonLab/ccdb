package org.jlab.ccdb

import java.util.ArrayList

/**
 * Gets statistics of ccdb requests
 */
public class RequestStatistics{

    /**
     * A list of requests
     */
    public val requests:ArrayList<RequestParseResult> = ArrayList<RequestParseResult>()
    public var totalTime:Double = 0.0
    public var lastRequestTime:Double = 0.0

    /**
     * First data read after connection takes longer. So it is separated
     */
    public var firstTime:Double = 0.0

    public val averageTime:Double
        get(){
            if(requests.size == 0) return 0.0
            if(requests.size == 1) return firstTime
            return (totalTime-firstTime)/(requests.size -1)
        }

}
