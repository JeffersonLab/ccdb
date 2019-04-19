import posixpath
import datetime


def split(path):
    return posixpath.split(path)


class PathObject:

    def __init__(self):
        self.name = ""
        self.path = ""
        self.CCDBType = "Directory"
        self.tag = None


class PathObjectType:
    def __init__(self):
        pass

    Directory = "Directory"
    TypeTable = "TypeTable"
    Variation = "Variation"
    Run = "Run"


class ParseRequestResult(object):
    """@brief ParseRequestResult is a class that represents parse result of
    a string request. @see PathUtils::ParseRequest
    """

    def __init__(self):
        self.run = -1  # Run number
        self.run_is_parsed = False  # true if Run number was non empty
        self.path = ""  # Object path
        self.path_is_parsed = False  # true if Path was nonempty
        self.variation = ""  # Variation name
        self.variation_is_parsed = False  # true if variation was not empty
        self.time = datetime.datetime.now()  # Time stamp
        self.time_str = ""  # Original string with time
        self.time_is_parsed = False  # true if time stamp was not empty


# ______________________________________________________________________________
def extract_dir(path=""):
    return posixpath.dirname(path)


# ______________________________________________________________________________
def extract_name(path=""):
    return posixpath.basename(path)


# ______________________________________________________________________________
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


def parse_time(time_str="-1", max_time_by_default=True):
    """ @brief ParseTime
    parses time as any part of
    YYYY:MM:DD-hh:mm:ss

    1) in place of ':' and '-' might be any ONE non digit character

    2) One could place only part of the string,
       the latest date for this part will be returned.
       I.e. if timeString is "2011" - (it means the year 2011 and nothing more),
       this function returns result as if it were 2011:12:31-23:59:59
       thus using such timestamp would get the latest constants for year 2011

    :param max_time_by_default:
    :parameter time_str: timeString string to parse
    :return: result time object
    :rtype: datetime.datetime
    """

    # the function is ported from C++ dont be surprise by struct_time

    # default result
    if max_time_by_default:
        year = 2037
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

    # some tmp values
    tmp_str = ""  # tmp string to buffer chars
    delim_count = 0  # number of delimiters we've met

    work_str = time_str + ' '  # we appended a work string for one more non digit symbol
    # so the logic behind would work in any case
    last_is_digit = False  # last symbol was digit

    # scan all symbols
    for symbol in work_str:

        if '0' <= symbol <= '9':  # Check if it is number
            tmp_str = tmp_str + symbol
            last_is_digit = True

        elif last_is_digit:  # it is a delimiter after the value;
            delim_count += 1

            # it was a year
            if delim_count == 1:
                if len(tmp_str) != 4:
                    raise ValueError("The year length !=4")  # it is an error with length of year
                year = int(tmp_str)  # since in tm the year is from 1900

            # it was a month
            if delim_count == 2:
                if len(tmp_str) != 2:
                    raise ValueError("The month length !=2")  # it is an error with length of month
                month = int(tmp_str)

                # check for 30 day month
                if month in [9, 4, 6, 10]:
                    day = 30
                if month == 2:
                    if year % 4 == 0 and year % 100 != 0 or year % 400 == 0:
                        day = 29
                    else:
                        day = 28

            # it was a day
            if delim_count == 3:
                if len(tmp_str) != 2:
                    raise ValueError("The day length !=2")  # it is an error with length of day
                day = int(tmp_str)

            # it was an hour
            if delim_count == 4:
                if len(tmp_str) != 2:
                    raise ValueError("The hour length !=2")  # it is an error with length of hour
                hour = int(tmp_str)

            # it was a min
            if delim_count == 5:
                if len(tmp_str) != 2:
                    raise ValueError("The minutes length !=2")  # it is an error with length of minutes
                minute = int(tmp_str)

            # it was a sec
            if delim_count == 6:
                if len(tmp_str) != 2:
                    raise ValueError("The sec length !=2")  # it is an error with length of sec
                second = int(tmp_str)

            # clear temp string for the next digits
            tmp_str = ""

        else:
            tmp_str = ""  # in this case we clear temp string too

    return datetime.datetime(year=year, month=month, day=day, hour=hour, minute=minute, second=second)


def parse_request(request_str=""):
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

    # Set the default parameters
    result = ParseRequestResult()
    result.run = 0                      # Run number
    result.run_is_parsed = False        # true if Run number was non empty
    result.run_is_invalid = False       # true if was an error parsing run-number
    result.path = ""                    # Object path
    result.path_is_parsed = False       # true if Path was nonempty
    result.variation = ""               # Variation name
    result.variation_is_parsed = False  # true if variation was not empty
    result.time = 0                     # Time stamp
    result.time_is_parsed = False       # true if time stamp was not empty
    result.time_str = ""                # Original string with time

    colon_count = 0
    run_str = ""
    for symbol in request_str:
        if symbol != ':':
            # it is not a colon so we add this symbol somewhere

            # it is a path
            if colon_count == 0:
                result.path += symbol
                result.path_is_parsed = True

            # it is a run range
            elif colon_count == 1:
                run_str += symbol
                result.run_is_parsed = True

            # it is a variation
            elif colon_count == 2:
                result.variation += symbol  # Variation name
                result.variation_is_parsed = True  # True since we've got a variation

            # it should be a time than
            else:
                result.time_is_parsed = True  # true if time stamp was not empty
                result.time_str += symbol  # Original string with time
        else:  # the symbol is colon (symbol==':')
            if colon_count == 3:
                result.time_str += symbol  # it is colon but we are parsing time now, so it is related to time
            else:
                colon_count += 1

    # at this point we parsed all symbols and it is time for final parsing

    # parse run number
    if result.run_is_parsed:
        result.run = int(run_str)
        result.run_is_invalid = False

    # parse time
    if result.time_is_parsed:
        result.time = parse_time(result.time_str)

    return result


def validate_name(name):
    """ Checks if name is valid ccdb object name
    :return: True if name is correct
    :rtype: bool
    """
    import re
    if re.match(r"^[\w]+$", name):
        return True  # No match
    return False


def make_absolute(path=""):
    """    /** @brief Adds '/' to the beginning of the path if it is not there
    *
    * If one have 'the/path' this function will change the string as '/the/path'
    * If one gave '/the/path' this function does nothing
    * @parameter [in] string & path
    * @return   void
    */"""

    if is_absolute(path):
        return '/' + path
    return path


# ______________________________________________________________________________
def is_absolute(path=""):
    """ @brief Check if the path is absolute - starts with """

    return path[0] == '/'
