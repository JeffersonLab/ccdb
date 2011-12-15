import posixpath
import datetime
import time as time_lib

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


class ParseRequestResult:
    """@brief ParseRequestResult is a class that represents parse result of
    a string request. @see PathUtils::ParseRequest
    """

    RunNumber = -1 	       # Run number
    IsInvalidRunNumber = False # true if was an error parsing runnumber
    Path=""                    # Object path
    WasParsedPath=False        # true if Path was nonempty
    Variation="";              # Variation name
    Time = 0                   # Time stampt
    Time = 0                   # Time stampt
    TimeString = ""            # Original string with time
    WasParsedTime = False      # true if time stampt was not empty
    WasParsedRunNumber=False   # true if Run number was non empty
    WasParsedVariation=False   # true if variation was not empty
    

#______________________________________________________________________________
def extract_dir(path = ""):
    return posixpath.dirname(path)


#______________________________________________________________________________
def extract_name(path=""):
    return posixpath.basename(path);


#______________________________________________________________________________
def join(left = "", right = "" ):
    return posixpath.join(left,right)

#______________________________________________________________________________
def parse_time(timeStr="-1"):
    """ @brief ParseTime
    parses time as any part of
    YYYY:MM:DD-hh:mm:ss

    1) in place of ':' and '-' might be any ONE non digit character

    2) One could place only part of the string,
       the latest date for this part will be returned.
       I.e. if timeString is "2011" - (it means the year 2011 and nothing more),
       this function returns result as if it were 2011:12:31-23:59:59
       thus using such timestamp would get the latest constants for year 2011

    @parameter [in] const string & timeString string to parse
    @parameter [out] succsess true if success
    @return   time_t
    """
    
    #the function is ported from C++ dont be surprise by struct_time
    
    #default result
    succsess = True
    year=2037
    month = 12
    day = 31
    hour = 23
    minute = 59
    second = 59

    #some tmp values
    tmpStr =""     #tmp string to buffer chars
    delimCount=0   #number of delimeters we've met

    workStr=timeStr + ' '    #we appended a work string for one more non digit symbol
                             #so the logic behind would work in any case
    lastIsDigit=False;       #last symbol was digit

    #scan all symbols
    for symbol in workStr:

        if symbol >= '0' and symbol <= '9':  # Check if it is number
            tmpStr = tmpStr + symbol
            lastIsDigit = True

        elif lastIsDigit: #it is a delimeter after the value;
            delimCount+=1

            #it was a year
            if delimCount == 1:  
                if len(tmpStr) !=4: raise ValueError("The year length !=4")    #it is an error with lengtn of year
                year = int(tmpStr);                                      #since in tm the year is from 1900

            #it was a month
            if delimCount == 2: 
                if len(tmpStr) !=2:  raise ValueError("The month length !=2") #it is an error with lengtn of month
                month = int(tmpStr)

                #check for 30 day month
                if month in [9, 4, 6, 10]:
                    day = 30
                if month == 2:
                    if year % 4 == 0 and  time.year % 100 != 0 or time.year % 400 == 0:
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

            #clear temp string for the next digit seria
            tmpStr="";

        else:
            tmpStr="" #in this case we clear temp string too
    #//for    
    time = datetime.datetime(year=year, month = month, day = day, hour = hour, minute = minute, second = second)
    result = time_lib.mktime(time.timetuple())
    return result


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
    @return structure that represent user result
    """

    #Set the default parameters
    result = ParseRequestResult();
    result.RunNumber=0;	              # Run number
    result.WasParsedRunNumber=False;  # true if Run number was non empty
    result.IsInvalidRunNumber=False;  # true if was an error parsing runnumber
    result.Path = "";                 # Object path
    result.WasParsedPath=False;       # true if Path was nonempty
    result.Variation="";              # Variation name
    result.WasParsedVariation=False;  # true if variation was not empty
    result.Time=0;                    # Time stamp
    result.WasParsedTime=False;       # true if time stamp was not empty
    result.TimeString="";             # Original string with time

    colonCount=0
    runStr ="";
    for symbol in requestStr:
        if(symbol!=':'):
            #it is not a colon so we add this symbol somewhere

            #it is a path
            if colonCount == 0:
                result.Path+=symbol
                result.WasParsedPath=True

            #it is a run range
            elif colonCount == 1:  
                runStr+=symbol
                result.WasParsedRunNumber = True

            #it is a variation
            elif colonCount == 2:  
                result.Variation+=symbol         # Variation name
                result.WasParsedVariation=True   # True since we've got a variation

            #it should be a time than
            else:  
                result.WasParsedTime=True        # true if time stampt was not empty
                result.TimeString+=symbol        # Original string with time
        else: #the symbol is colon (symbol==':')
            colonCount+=1

    # at this point we parsed all symbols and it is time for final parsing

    #parse run number
    if result.WasParsedRunNumber :
        try:
            result.RunNumber = int(runStr)
            result.IsInvalidRunNumber = False
        except:
            result.IsInvalidRunNumber = True

    #parse time
    if result.WasParsedTime:
        try:
            result.Time = parse_time(result.TimeString)
        except:
            raise

    return result


#______________________________________________________________________________
def MakeAbsolute(path=""):
    """    /** @brief Adds '/' to the beginning of the path if it is not there
    *
    * If one have 'the/path' this function will change the string as '/the/path'
    * If one gave '/the/path' this function does nothing
    * @parameter [in] string & path
    * @return   void
    */"""

    if IsAbsolute(path): return '/' + path
    return path;


#______________________________________________________________________________
def IsAbsolute( path="" ):
    """ @brief Check if the path is absolute - starts with """

    return path[0]=='/'