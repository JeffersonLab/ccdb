package org.jlab.ccdb

//Set default parameters
// result
import java.util.Date

class RequestParseResult(
        public val originalRequest:String
) {
    /** Run number */
    public var runNumber:Int=0

    /** true if Run number was non empty */
    public var wasParsedRunNumber:Boolean=false

    /** true if was an error parsing run number */
    public var isInvalidRunNumber:Boolean=false

    /** Object path **/
    public var path:String = ""

    /** true if Path was nonempty */
    public var wasParsedPath:Boolean=false

    /** Variation name */
    public var variation:String=""

    /** true if variation was not empty */
    public var wasParsedVariation:Boolean=false

    /** Time stamp */
    public var time:Date = Date(0)

    /** true if time stamp was not empty */
    public var wasParsedTime:Boolean=false

    /** Original string with time */
    public var timeString:String=""
}
