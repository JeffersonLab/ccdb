import posixpath
import datetime
import calendar


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


class ParseRequestResult:
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
        self.tag = ""  # Tag name, the part after '@'
        self.tag_is_parsed = False  # true if tag was not empty
        self.original_str = ""  # The request string as given


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


TIME_GROUP_LENGTHS = (4, 2, 2, 2, 2, 2)    # YYYY MM DD hh mm ss; a seventh group is the fraction, 1 to 6 digits


def parse_time(time_str="-1", max_time_by_default=True):
    """Parses a time a person types: local wall time, any leading part of YYYY-MM-DD hh:mm:ss.ffffff

    Groups of digits separated by exactly one non-digit character of any kind: "2024-03-01 12:30:15.25",
    "2024-03-01_12-30-15", "2024/03". The fraction group has 1 to 6 digits.

    A partial time is the latest moment it covers (docs/concepts/time.md): "2011" is 2011-12-31 23:59:59.999999,
    "2024-02" is 2024-02-29 23:59:59.999999, "12:00:00" is 12:00:00.999999 and "12:00:00.5" is 12:00:00.599999,
    so constants added any time within the named part count. With max_time_by_default=False the missing parts are
    the earliest moment instead (the fraction padded with zeros).

    The C++ library reads the same text the same way (TimeUtils::ParseLocalTime); testdata/time/parse_cases.tsv
    holds the cases both run. local_to_utc gives the UTC instant of the result.

    :param time_str: the text
    :param max_time_by_default: True: missing parts are the latest moment they cover
    :return: naive local wall time with microseconds (fold=0)
    :rtype: datetime.datetime
    :raises ValueError: the text does not follow the grammar or names an impossible date
    """
    import re
    if not re.match(r"^\d+(\D\d+){0,6}$", time_str):
        raise ValueError("Can't read the time '{0}': expected YYYY-MM-DD hh:mm:ss.ffffff or a leading part of it"
                         .format(time_str))
    groups = re.findall(r"\d+", time_str)
    for group, length, name in zip(groups, TIME_GROUP_LENGTHS, ("year", "month", "day", "hour", "minute", "second")):
        if len(group) != length:
            raise ValueError("Can't read the time '{0}': the {1} must have {2} digits".format(time_str, name, length))
    if len(groups) == 7 and len(groups[6]) > 6:
        raise ValueError("Can't read the time '{0}': at most 6 digits after the seconds".format(time_str))

    year = int(groups[0])
    month = int(groups[1]) if len(groups) > 1 else (12 if max_time_by_default else 1)
    if not 1 <= month <= 12:
        raise ValueError("Can't read the time '{0}': month {1}".format(time_str, month))
    days_in_month = calendar.monthrange(year, month)[1]
    defaults = (days_in_month, 23, 59, 59) if max_time_by_default else (1, 0, 0, 0)
    day, hour, minute, second = [int(groups[2 + i]) if len(groups) > 2 + i else defaults[i] for i in range(4)]
    if not (1 <= day <= days_in_month and hour <= 23 and minute <= 59 and second <= 59):
        raise ValueError("Can't read the time '{0}': no such date or time".format(time_str))
    fraction = groups[6] if len(groups) == 7 else ""
    microsecond = int(fraction.ljust(6, "9" if max_time_by_default else "0"))
    return datetime.datetime(year, month, day, hour, minute, second, microsecond)


def local_to_utc(local_time):
    """The UTC instant of a naive local wall time, as an aware datetime

    A wall time that occurs twice (the hour after daylight saving ends) or never (the hour skipped when it starts)
    is read with the UTC offset in effect before the transition, as `fold=0` says (PEP 495); a value with
    fold=1, as utc_to_local makes for the second occurrence, keeps it. An aware datetime is converted as it is.
    The C++ library implements the same rule (TimeUtils::LocalWallToUtc).
    """
    if local_time.tzinfo is not None:
        return local_time.astimezone(datetime.timezone.utc)
    seconds = int(local_time.replace(microsecond=0).timestamp())
    return datetime.datetime.fromtimestamp(seconds, datetime.timezone.utc).replace(microsecond=local_time.microsecond)


def utc_to_local(utc_time):
    """The naive local wall time of a UTC instant (an aware datetime, or a naive one that holds UTC)

    `fold` is set on the second occurrence of a repeated hour, so local_to_utc gives the instant back.
    """
    if utc_time.tzinfo is None:
        utc_time = utc_time.replace(tzinfo=datetime.timezone.utc)
    seconds = int(utc_time.replace(microsecond=0).timestamp())
    return datetime.datetime.fromtimestamp(seconds).replace(microsecond=utc_time.microsecond)


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

    A tag ends the request after '@' and replaces the variation and the time:
    /path/to/data@mytag or /path/to/data:run@mytag
    A request with a tag and a variation or a time is an error.

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
    result.tag = ""                     # Tag name
    result.tag_is_parsed = False        # true if tag was not empty
    result.original_str = request_str   # The request string as given

    # neither paths, nor runs, nor variations, nor times contain '@', so the first one starts the tag
    if '@' in request_str:
        request_str, tag = request_str.split('@', 1)
        if not validate_tag_name(tag):
            raise ValueError("Tag name '{0}' in request '{1}' is invalid. "
                             "It should consist of A-Z, a-z, 0-9, _".format(tag, result.original_str))
        result.tag = tag
        result.tag_is_parsed = True

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

    if result.tag_is_parsed and (result.variation_is_parsed or result.time_is_parsed):
        raise ValueError("A request with a tag can have neither a variation nor a time: '{0}'"
                         .format(result.original_str))

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


def validate_tag_name(name):
    """ Checks if name is a valid tag name: ASCII letters, digits and '_' only
    :return: True if name is correct
    :rtype: bool
    """
    import re
    return re.fullmatch(r"[A-Za-z0-9_]+", name) is not None


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
