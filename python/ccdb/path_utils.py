import posixpath
import datetime


def split(path):
    return posixpath.split(path)


class PathObject():

    def __init__(self):
        self.name = ""
        self.path = ""
        self.CCDBType = "Directory"
        self.tag = None


class PathObjectType:
    Directory = "Directory"
    TypeTable = "TypeTable"
    Variation = "Variation"
    Run = "Run"


class ParseRequestResult(object):
    """@brief ParseRequestResult is a class that represents parse result of
    a string request. @see PathUtils::ParseRequest
    """

    def __init__(self):
        self.run = -1 	                     # Run number
        self.run_is_parsed = False           # true if Run number was non empty
        self.path = ""                       # Object path
        self.path_is_parsed = False          # true if Path was nonempty
        self.variation = ""                  # Variation name
        self.variation_is_parsed = False     # true if variation was not empty
        self.time = datetime.datetime.now()  # Time stamp
        self.time_str = ""                   # Original string with time
        self.time_is_parsed = False          # true if time stamp was not empty


#______________________________________________________________________________
def extract_dir(path=""):
    return posixpath.dirname(path)


#______________________________________________________________________________
def extract_name(path=""):
    return posixpath.basename(path)


#______________________________________________________________________________
def join(a, *p):
    """Join two or more pathname components, inserting '/' as needed.
    If any component is an absolute path, all previous path components
    will be discarded.  An empty last part will result in a path that
    ends with a separator."""
    path = a
    for b in p:
        if b.startswith('/'):
            path = b
        elif path == '' or path.endswith('/'):
            path += b
        else:
            path += '/' + b
    return path


#______________________________________________________________________________
def parse_time(timeStr="-1", max_time_by_default=True):
    """ @brief ParseTime
    parses time as any part of
    YYYY:MM:DD-hh:mm:ss

    1) in place of ':' and '-' might be any ONE non digit character

    2) One could place only part of the string,
       the latest date for this part will be returned.
       I.e. if timeString is "2011" - (it means the year 2011 and nothing more),
       this function returns result as if it were 2011:12:31-23:59:59
       thus using such timestamp would get the latest constants for year 2011

    :parameter timeStr: timeString string to parse
    :return: result time object
    :rtype: datetime.datetime
    """
    
    #the function is ported from C++ dont be surprise by struct_time
    
    #default result
    if max_time_by_default:
        year=2037
        month = 12
        day = 31
        hour = 23
        minute = 59
        second = 59
    else:
        year = 2000
        month = 1
        day = 1
        hour = 0
        minute = 0
        second = 0

    #some tmp values
    tmpStr =""     #tmp string to buffer chars
    delimCount=0   #number of delimeters we've met

    workStr=timeStr + ' '    #we appended a work string for one more non digit symbol
                             #so the logic behind would work in any case
    lastIsDigit=False        #last symbol was digit

    #scan all symbols
    for symbol in workStr:

        if '0' <= symbol <= '9':  # Check if it is number
            tmpStr = tmpStr + symbol
            lastIsDigit = True

        elif lastIsDigit: #it is a delimeter after the value;
            delimCount+=1

            #it was a year
            if delimCount == 1:  
                if len(tmpStr) !=4: raise ValueError("The year length !=4")    #it is an error with lengtn of year
                year = int(tmpStr)                                             #since in tm the year is from 1900

            #it was a month
            if delimCount == 2: 
                if len(tmpStr) !=2:  raise ValueError("The month length !=2") #it is an error with lengtn of month
                month = int(tmpStr)

                #check for 30 day month
                if month in [9, 4, 6, 10]:
                    day = 30
                if month == 2:
                    if year % 4 == 0 and  year % 100 != 0 or year % 400 == 0:
                        day = 29
                    else:
                        day = 28


            #it was a day
            if delimCount == 3:
                if len(tmpStr) !=2:  raise ValueError("The day length !=2") #it is an error with lengtn of day
                day = int(tmpStr)

            #it was a hour
            if delimCount == 4: 
                if len(tmpStr) !=2:  raise ValueError("The hour length !=2") #it is an error with lengtn of hour
                hour = int(tmpStr)

            #it was a min
            if delimCount == 5: 
                if len(tmpStr) !=2:  raise ValueError("The minutes length !=2") #it is an error with lengtn of minutes
                minute = int(tmpStr)

            #it was a sec
            if delimCount ==6:
                if len(tmpStr) !=2:  raise ValueError("The sec length !=2") #it is an error with lengtn of sec
                second = int(tmpStr)

            #clear temp string for the next digits
            tmpStr=""

        else:
            tmpStr="" #in this case we clear temp string too
    #//for    
    return datetime.datetime(year=year, month = month, day = day, hour = hour, minute = minute, second = second)
    #result = time_lib.mktime(time.timetuple())
    #return result


#______________________________________________________________________________
def parse_request( requestStr="" ):
    """ @brief    Parses request string and returns corresponding 
    @see ParseRequestResult structure. 

    This function is used to parse user requests. The user requests 
    full form of request is 
    /path/to/data:run:variation:time
    but request might be given in any shorter form
    /path/to/data - just path to date, no run, variation and timestamp specified
    /path/to/data::mc - no run or date specified.
    /path/to/data:::2029 - only path and date

    @parameter [in] requestStr - user request
    :return: structure that represent user result
    :rtype: ParseRequestResult
    """

    #Set the default parameters
    result = ParseRequestResult()
    result.run=0	              # Run number
    result.run_is_parsed=False   # true if Run number was non empty
    result.run_is_invalid=False   # true if was an error parsing runnumber
    result.path = ""                  # Object path
    result.path_is_parsed=False        # true if Path was nonempty
    result.variation=""               # Variation name
    result.variation_is_parsed=False   # true if variation was not empty
    result.time=0                     # Time stamp
    result.time_is_parsed=False        # true if time stamp was not empty
    result.time_str=""              # Original string with time

    colonCount=0
    runStr =""
    for symbol in requestStr:
        if symbol!=':':
            #it is not a colon so we add this symbol somewhere

            #it is a path
            if colonCount == 0:
                result.path+=symbol
                result.path_is_parsed=True

            #it is a run range
            elif colonCount == 1:  
                runStr+=symbol
                result.run_is_parsed = True

            #it is a variation
            elif colonCount == 2:  
                result.variation+=symbol         # Variation name
                result.variation_is_parsed=True   # True since we've got a variation

            #it should be a time than
            else:  
                result.time_is_parsed=True        # true if time stampt was not empty
                result.time_str+=symbol        # Original string with time
        else: #the symbol is colon (symbol==':')
            if colonCount == 3: result.time_str+=symbol #it is colon but we are parsing time now, so it is related to time
            else: colonCount+=1

    # at this point we parsed all symbols and it is time for final parsing

    #parse run number

    if result.run_is_parsed :
        try:
            result.run = int(runStr)
            result.run_is_invalid = False
        except:
            raise

    #parse time
    if result.time_is_parsed:
        try:
            result.time = parse_time(result.time_str)
        except:
            raise

    return result


#______________________________________________________________________________
def validate_name(name):
    """ Checks if name is valid ccdb object name
    :return: True if name is correct
    :rtype: bool
    """
    import re
    if re.match("^[\w]+$", name):
        return True   # No match
    return False


#______________________________________________________________________________
def MakeAbsolute(path=""):
    """    /** @brief Adds '/' to the beginning of the path if it is not there
    *
    * If one have 'the/path' this function will change the string as '/the/path'
    * If one gave '/the/path' this function does nothing
    * @parameter [in] string & path
    * @return   void
    */"""

    if IsAbsolute(path):
        return '/' + path
    return path


#______________________________________________________________________________
def IsAbsolute( path="" ):
    """ @brief Check if the path is absolute - starts with """

    return path[0]=='/'