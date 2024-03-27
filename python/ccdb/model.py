import collections.abc
import datetime
import posixpath
from sqlalchemy import text

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.types import Integer, String, Text, DateTime, Enum, Boolean
from sqlalchemy.orm import reconstructor, relationship
from sqlalchemy.orm import relationship, backref

Base = declarative_base()

# This thing separates cells in data blob
blob_delimiter = "|"

# if cell of data table is a string and the string already contains blob_delimiter
# we have to encode blob_delimiter to blob_delimiter_replace on data write and decode it bach on data read
blob_delimiter_replacement = "&delimiter;"

# The default "infinite run" number
INFINITE_RUN = 2147483647

# noinspection PyClassHasNoInit
# --------------------------------------------
# class CcdbSchemaVersion
# --------------------------------------------
class CcdbSchemaVersion(Base):
    """
    Represents CCDB directory object.
    Directories may contain other directories or TypeTable objects
    """

    __tablename__ = 'schemaVersions'
    id = Column(Integer, primary_key=True)
    version = Column("schemaVersion", Integer, nullable=False, server_default=text("'1'"))

    def __repr__(self):
        return "<CcdbSchemaVersion {0} version: '{1}'>".format(self.id, self.version)


# --------------------------------------------
# class Directory
# --------------------------------------------
class Directory(Base):
    """
    Represents CCDB directory object.
    Directories may contain other directories or TypeTable objects
    """
    __tablename__ = 'directories'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, server_default=text("''"))
    comment = Column(Text)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    modified = Column(DateTime, nullable=False,
                      default=datetime.datetime.now,
                      onupdate=datetime.datetime.now,
                      server_default=text("'2007-01-01 00:00:00'"))
    parent_id = Column('parentId', Integer, nullable=False, index=True, server_default=text("'0'"))
    author_id = Column('authorId', Integer, default=1, nullable=False, server_default=text("'1'"))

    def __init__(self):
        self.path = ""
        self.parent_dir = None
        self.sub_dirs = []

    @reconstructor
    def on_load_init(self):
        self.path = ""
        self.parent_dir = None
        self.sub_dirs = []

    def __repr__(self):
        return "<Directory {0} '{1}'>".format(self.id, self.name)


# --------------------------------------------
# class TypeTable
# --------------------------------------------
# noinspection PyClassHasNoInit
class TypeTable(Base):
    __tablename__ = 'typeTables'
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String(255), nullable=False)
    comment = Column(Text)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    modified = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False, server_default=text("'2007-01-01 00:00:00'"))
    parent_dir_id = Column('directoryId', Integer, ForeignKey('directories.id'), nullable=False, index=True)
    parent_dir = relationship("Directory", backref=backref('type_tables', order_by=id))
    constant_sets = relationship("ConstantSet", backref=backref('type_table'))
    columns = relationship("TypeTableColumn",
                           order_by="TypeTableColumn.order",
                           cascade="all, delete, delete-orphan",
                           backref=backref("type_table"))
    rows_count = Column('nRows', Integer, nullable=False, server_default=text("'1'"))
    _columns_count = Column('nColumns', Integer, nullable=False)
    author_id = Column('authorId', Integer, default=1, nullable=False)

    @property
    def columns_count(self):
        """
        :return: Number of columns of the table
        :rtype: int
        """
        return self._columns_count

    @property
    def path(self):
        """
        :return: full path of the table
        :rtype: str
        """
        return posixpath.join(self.parent_dir.path, self.name)

    def __repr__(self):
        return "<TypeTable {0} '{1}'>".format(self.id, self.name)


# --------------------------------------------
# class TypeTableColumn
# --------------------------------------------
# noinspection PyClassHasNoInit
class TypeTableColumn(Base):
    __tablename__ = 'columns'
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String(45), nullable=False)
    comment = Column(Text)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    modified = Column(DateTime, nullable=False,
                      default=datetime.datetime.now,
                      onupdate=datetime.datetime.now,
                      server_default=text("'2007-01-01 00:00:00'"))
    order = Column(Integer, nullable=False)
    type = Column('columnType', Enum('int', 'uint', 'long', 'ulong', 'double', 'string', 'bool'))
    type_table_id = Column('typeId', Integer, ForeignKey('typeTables.id'), nullable=False, index=True)

    # TODO remove this comments!
    # @property
    # def path(self):
    #     return posixpath.join(self.parent_dir.path, self.name)

    def __repr__(self):
        return "<TypeTableColumn '{0}'>".format(self.name)


# --------------------------------------------
# class ConstantSet
# --------------------------------------------
# noinspection PyClassHasNoInit,PyUnresolvedReferences
class ConstantSet(Base):
    __tablename__ = 'constantSets'
    id = Column(Integer, primary_key=True, unique=True)
    _vault = Column('vault', Text, nullable=False)
    created = Column(DateTime, default=datetime.datetime.now, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    modified = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False, server_default=text("'2007-01-01 00:00:00'"))
    type_table_id = Column('constantTypeId', Integer, ForeignKey('typeTables.id'), nullable=False, index=True)
    assignments = relationship("Assignment", uselist=True, back_populates="constant_set")
   

    @property
    def vault(self):
        """
        Text-blob with data as it is presented in database
        :return: string with text-blob from db
        :rtype:  string
        """
        return self._vault

    @property
    def data_list(self):
        return blob_to_list(self._vault)

    @data_list.setter
    def data_list(self, data_list):
        self._vault = list_to_blob(data_list)

    @property
    def data_table(self):
        return list_to_table(self.data_list, self.type_table.columns_count)

    @data_table.setter
    def data_table(self, data):
        self.data_list = list(gen_flatten_data(data))

    def __repr__(self):
        return "<ConstantSet '{0}'>".format(self.id)


# --------------------------------------------
# class Assignment
# --------------------------------------------
# noinspection PyClassHasNoInit,PyUnresolvedReferences
class Assignment(Base):
    __tablename__ = 'assignments'

    id = Column(Integer, primary_key=True, unique=True)
    created = Column(DateTime, nullable=False, index=True,
                     default=datetime.datetime.now,
                     server_default=text("CURRENT_TIMESTAMP"))
    modified = Column(DateTime, nullable=False,
                      default=datetime.datetime.now,
                      onupdate=datetime.datetime.now,
                      server_default=text("'2007-01-01 00:00:00'"))
    constant_set_id = Column('constantSetId', Integer, ForeignKey('constantSets.id'), nullable=False)
    constant_set = relationship("ConstantSet",
                                uselist=False,
                                back_populates="assignments",
                                cascade="all, delete, delete-orphan",
                                single_parent=True)
    
    run_range_id = Column('runRangeId', Integer, ForeignKey('runRanges.id'), index=True)
    run_range = relationship("RunRange", backref=backref('assignments'))
    variation_id = Column('variationId', Integer, ForeignKey('variations.id'), nullable=False, index=True)
    variation = relationship("Variation", backref=backref('assignments'))
    _comment = Column('comment', Text)
    author_id = Column('authorId', Integer, ForeignKey('users.id'), default=1, nullable=False)
    author = relationship("User", uselist=False)

    _event_range_id = Column('eventRangeId', Integer, index=True)

    @property
    def comment(self):
        """
        returns comment for the object
        :rtype: basestring
        """
        return self._comment if self._comment is not None else ""

    @comment.setter
    def comment(self, value):
        self._comment = value

    @property
    def request(self):
        """
        Gets the unique "request" string in form of <path>:<run>:<variation>:<time>
        :rtype: basestring
        """

        path = self.constant_set.type_table.path
        run = self.run_range.min
        variation = self.variation.name
        time = self.created.strftime("%Y-%m-%d_%H-%M-%S")

        return "{0}:{1}:{2}:{3}".format(path, run, variation, time)

    def __repr__(self):
        return "<Assignment '{0}'>".format(self.id)

    def print_info(self):
        print((" ASSIGNMENT: " + repr(self)
              + " TABLE: " + repr(self.constant_set.type_table)
              + " RUN RANGE: " + repr(self.run_range)
              + " VARIATION: " + repr(self.variation)
              + " SET: " + repr(self.constant_set)))
        print("      |")
        print("      +-->" + repr(self.constant_set.vault))
        print("      +-->" + repr(self.constant_set.data_list))
        print("      +-->" + repr(self.constant_set.data_table))


# --------------------------------------------
# class EventRange
# --------------------------------------------
# noinspection PyClassHasNoInit
class EventRange(Base):
    __tablename__ = 'eventRanges'

    id = Column(Integer, primary_key=True, unique=True)
    created = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    modified = Column(DateTime, nullable=False, server_default=text("'2007-01-01 00:00:00'"))
    runNumber = Column(Integer, nullable=False)
    eventMin = Column(Integer, nullable=False)
    eventMax = Column(Integer, nullable=False)
    comment = Column(Text)


# --------------------------------------------
# class RunRange
# --------------------------------------------
# noinspection PyClassHasNoInit
class RunRange(Base):
    __tablename__ = 'runRanges'
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String(45))
    created = Column(DateTime, default=datetime.datetime.now, nullable=False, server_default=text("'2007-01-01 00:00:00'"))
    modified = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    comment = Column(Text)
    min = Column('runMin', Integer, nullable=False)
    max = Column('runMax', Integer, nullable=False)

    def __repr__(self):
        if self.name != "":
            return "<RunRange {0} {3}:{1}-{2}>".format(self.id, self.min, self.max, self.name)
        else:
            return "<RunRange {0} '{1}-{2}'>".format(self.id, self.min, self.max)


# --------------------------------------------
# class Variation
# --------------------------------------------
# noinspection PyClassHasNoInit
class Variation(Base):
    __tablename__ = 'variations'
    id = Column(Integer, primary_key=True, unique=True)
    name = Column(String(100), nullable=False, index=True, server_default=text("'default'"))
    created = Column(DateTime, nullable=False,
                     server_default=text("'2007-01-01 00:00:00'"), default=datetime.datetime.now)
    modified = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), default=datetime.datetime.now)
    comment = Column(Text)
    author_id = Column('authorId', Integer, nullable=False, server_default=text("'1'"), default=1)
    parent_id = Column('parentId', Integer, ForeignKey('variations.id'), nullable=False, index=True,
                       server_default=text("'1'"), default=1)
    parent = relationship('Variation', remote_side=[id], back_populates='children')
    children = relationship("Variation", back_populates='parent')

    is_locked = Column('isLocked', Boolean, nullable=False, default=True)
    lock_time = Column('lockTime', DateTime, default=datetime.datetime.now, nullable=False)

    _description = Column("description", String(255))   # (!) Deprecated! Is here for C++ compatibility with 1.06.1

    def __repr__(self):
        return "<Variation {0} '{1}'>".format(self.id, self.name)


#--------------------------------------------
# class User
#--------------------------------------------
# noinspection PyClassHasNoInit
class User(Base):
    """
    Represent user of the ccdb. Used for logging and authentication
    """
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, unique=True)
    created = Column('created', DateTime, default=datetime.datetime.now, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    last_action_time = Column('lastActionTime', DateTime, nullable=False,)
    name = Column(String(100), nullable=False)
    password = Column(String(100))
    _roles_str = Column('roles', String, nullable=False)
    info = Column(String(125), nullable=False)
    is_deleted = Column('isDeleted', Boolean, nullable=False, default=False)

    @property
    def roles(self):
        """
        Returns a list of user roles
        :rtype:[]
        """
        return self._roles_str.split(",")

    @roles.setter
    def roles(self, value):
        if not value:
            self._roles_str = ""
        else:
            self._roles_str = ",".join(value)


#--------------------------------------------
# class LogRecord - record logs
#--------------------------------------------
# noinspection PyClassHasNoInit
class LogRecord(Base):
    """
    One record to the log
    """
    __tablename__ = 'logs'
    id = Column(Integer, primary_key=True, unique=True)
    created = Column('created', DateTime, default=datetime.datetime.now, nullable=False, server_default=text("CURRENT_TIMESTAMP"))
    affected_ids = Column('affectedIds', String, nullable=False)
    action = Column(String(7), nullable=False)
    description = Column(String(255), nullable=False)
    comment = Column(String, nullable=True)
    author_id = Column('authorId', Integer, ForeignKey('users.id'), nullable=False, index=True)
    author = relationship("User")


# --------------------------------------------
#         R I G H T S  &  R O L E S
# --------------------------------------------
_roles_descr = {
    "user_create":              "Can create new user",
    "user_modify":              "Can modify users and set user roles",

    "assignment_add_own":        "Can add assignment to own variation",
    "assignment_add_nondefault": "Can add assignment to any variation except the default",
    "assignment_add_default":    "Can add assignment to the default variation",
    "assignment_modify":         "Can modify or even delete assignments. Exceptional role",

    "variation_create":          "Can create new variation",
    "variation_modify_own":      "Can modify self created variation",
    "variation_modify_any":      "Can modify any variation",
    "variation_delete_own":      "Can delete self created variation",
    "variation_delete_any":      "Can delete any variation",

    "runrange_create":           "Can create new runrange",
    "runrange_modify_own":       "Can modify self created runrange",
    "runrange_modify_any":       "Can modify any runrange",
    "runrange_delete_own":       "Can delete self created runrange",
    "runrange_delete_any":       "Can delete any runrange",

    "eventrange_create":         "Can create new eventrange",
    "eventrange_modify_own":     "Can modify self created eventrange",
    "eventrange_modify_any":     "Can modify any eventrange",
    "eventrange_delete_own":     "Can delete self created eventrange",
    "eventrange_delete_any":     "Can delete any eventrange",

    "table_create":              "Can create new table",
    "table_modify_own":          "Can modify self created table",
    "table_modify_any":          "Can modify any table",
    "table_delete_own":          "Can delete self created table",
    "table_delete_any":          "Can delete any table",

    "directory_create":          "Can create new directory",
    "directory_modify_own":      "Can modify self created directory",
    "directory_modify_any":      "Can modify any directory",
    "directory_delete_own":      "Can delete self created directory",
    "directory_delete_any":      "Can delete any directory",
}


_roles = list(_roles_descr.keys())

_default_roles = [
    "assignment_add_own",

    "variation_create",
    "variation_modify_own",
    "variation_delete_own",

    "runrange_create",
    "runrange_modify_own",
    "runrange_delete_own",

    "eventrange_create",
    "eventrange_modify_own",
    "eventrange_delete_own",

    "table_create",
    "table_modify_own",
    "table_delete_own",

    "directory_create",
    "directory_modify_own",
    "directory_delete_own"
]


# --------------------------------------------
# flattens arrays of arrays to one array
# --------------------------------------------
def get_roles():
    """
    Returns list of all known roles
    :return:
    """
    global _roles
    return _roles


# --------------------------------------------
# flattens arrays of arrays to one array
# --------------------------------------------
def gen_flatten_data(data):
    """
    get generator that flattens 'arrays of arrays' to one array

    :param data: List which probably contains sub-collections
    :type data: []
    :return: flattened list
    :rtype: generator

    example
    >>>list(gen_flatten_data([[[1, 2, 3], [4, 5]], "abs"]))
    [1, 2, 3, 4, 5, "abs"]

    """
    # python 3 hack to basestr
    try:
        u = str
    except NameError:
        # 'unicode' is undefined, must be Python 3
        check_type = str
    else:
        # 'unicode' exists, must be Python 2

        check_type = str

    for el in data:
        if isinstance(el, collections.abc.Iterable) and not isinstance(el, check_type):
            for sub in gen_flatten_data(el):
                yield sub
        else:
            yield el


# --------------------------------------------
# flattens arrays of arrays to one array
# --------------------------------------------
def flatten_data(data):
    """
     flattens arrays of arrays to one array

    :param data: List which probably contains sub-collections
    :type data: []
    :return: flattened list
    :rtype: generator

    example
    >>>flatten_data([[[1, 2, 3], [4, 5]], "abs"])
    [1, 2, 3, 4, 5, "abs"]

    """
    return list(gen_flatten_data(data))


# --------------------------------------------
#   Get tabled data, convert it to string blob for db insertion
# --------------------------------------------
def list_to_blob(data):
    """
    Get tabled data, convert it to string blob for db insertion

    if you have tabled data use gen_flatten_data to flatten data first


    :param data: FLATTENED list of values
    :type data: []
    :return: string with text-blob for database insertion
    :rtype: str

    >>>list_to_blob([1,"2","str"])
    "1|2|str"
    >>>list_to_blob(["strings", "with|surprise"])
    "strings|with&delimiter;surprise"
    """
    def prepare_item(p_item):
        if not isinstance(p_item, str):
            item_str = repr(p_item)
        else:
            item_str = p_item
        return item_str.replace(blob_delimiter, blob_delimiter_replacement)

    if len(data) == 0:
        return ""
    if len(data) == 1:
        return prepare_item(data[0])

    # this for data[:-1] makes result like a1|a2|a3
    blob = ""
    for item in data[:-1]:
        blob += prepare_item(item) + blob_delimiter
    blob += prepare_item(data[-1])

    return blob


# --------------------------------------------
# Get blob data and convert it to list decoding blob_delimiter
# --------------------------------------------
def blob_to_list(blob):
    """
    Get blob data and convert it to list decoding blob_delimiter

    :param blob:
    :type blob: str
    :return:

    >>>blob_to_list("1|2|str")
    ["1","2","str"]

    >>>blob_to_list("strings|with&delimiter;surprise")
    ["strings", "with|surprise"]
    """
    splits = blob.split(blob_delimiter)
    items = []
    for item in splits:
        items.append(item.replace(blob_delimiter_replacement, blob_delimiter))
    return items


# --------------------------------------------
# Converts flat array to tabled array
# --------------------------------------------
def list_to_table(data, col_count):
    """
    Converts flat array to tabled array

    :param data: flat list with data
    :type data: []
    :param col_count:number of columns
    :type col_count: int
    :return: tabled data
    :rtype:[]

    >>> list_to_table([1,2,3,4,5,6], 3)
    [[1,2,3],[4,5,6]]
    """

    if len(data) % col_count != 0:
        message = "Cannot convert list to table. " \
                  "The total number of cells ({0}) is not compatible with the number of columns ({1})"\
            .format(len(data), col_count)
        raise ValueError(message)

    row_count = len(data) // col_count
    # cpp way
    tabled_data = []
    for row_i in range(row_count):
        row = []
        for col_i in range(col_count):
            row.append(data[row_i * col_count + col_i])
        tabled_data.append(row)
    return tabled_data


# --------------------------------
#  parse_run_range
# --------------------------------
def parse_run_range(run_range_str):
    """ @brief parse run range string in form of <run_min>-<run-max>

        if one inputs '<run_min>-' this means <run_min>-<infinite run>
        if one inputs '-<run_max>' this means <0>-<run_max>

        @return (run_min, run_max, run_min_set, run_max_set)
        run_min_set, run_max_set - are flags indicating that values was set by user
        """

    assert isinstance(run_range_str, str)
    if not "-" in run_range_str:
        return None

    # split <>-<>
    (str_min, str_max) = run_range_str.split("-")
    run_min_set = False
    run_max_set = False

    # parse run min
    try:
        run_min = int(str_min)
        run_min_set = True
    except ValueError:
        run_min = 0

    # parse run max
    try:
        run_max = int(str_max)
        run_max_set = True
    except ValueError:
        run_max = INFINITE_RUN

    return run_min, run_max, run_min_set, run_max_set
