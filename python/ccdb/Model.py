__author__ = 'DmitryRa'

import datetime
import posixpath

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import sessionmaker, reconstructor
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy import desc


print sqlalchemy.__version__
engine = create_engine('mysql://ccdb_user@127.0.0.1/ccdb')
Base = declarative_base()


class Directory(Base):
    __tablename__ = 'directories'
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    comment = Column(Text)
    created = Column(DateTime, default = datetime.datetime.now)
    modified = Column(DateTime, default = datetime.datetime.now, onupdate = datetime.datetime.now)
    parent_id = Column('parentId', Integer)

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



class TypeTable(Base):
    __tablename__ = 'typeTables'
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    comment = Column("comments", Text)
    created = Column(DateTime, default = datetime.datetime.now)
    modified = Column(DateTime, default = datetime.datetime.now, onupdate = datetime.datetime.now)
    parent_dir_id = Column('directoryId',Integer, ForeignKey('directories.id'))
    parent_dir = relationship("Directory", backref=backref('type_tables', order_by=id))
    constant_sets = relationship("ConstantSet", backref=backref('type_table'))
    columns = relationship("TypeTableColumns", order_by="TypeTableColumns.order", cascade="all, delete, delete-orphan", backref("type_table") )
    rows_count = Column('nRows',Integer)
    _columns_count = Column('nColumns',Integer)

    @property
    def path(self):
        """
        :return: full path of the table
        :rtype: str
        """
        return posixpath.join(self.parent_dir.path, self.name)

    def __repr__(self):
        return "<TypeTable {0} '{1}'>".format(self.id, self.name)



class TypeTableColumn(Base):
    __tablename__ = 'columns'
    id = Column(Integer, primary_key=True)
    name = Column(String(255))
    comment = Column(Text)
    created = Column(DateTime, default = datetime.datetime.now)
    modified = Column(DateTime, default = datetime.datetime.now, onupdate = datetime.datetime.now)
    order = Column(Integer)
    type_table_id = Column('typeId',Integer, ForeignKey('typeTables.id'))


    @property
    def path(self):
        return posixpath.join(self.parent_dir.path, self.name)

    def __repr__(self):
        return "<TypeTableColumn '{0}'>".format(self.name)



class ConstantSet(Base):
    __tablename__ = 'constantSets'
    id = Column(Integer, primary_key=True)
    vault = Column('vault', Text)
    created = Column(DateTime, default = datetime.datetime.now)
    modified = Column(DateTime, default = datetime.datetime.now, onupdate = datetime.datetime.now)
    assignment = relationship("Assignment", uselist=False, backref="constant_set")
    type_table_id = Column('constantTypeId',Integer, ForeignKey('typeTables.id'))


    def __repr__(self):
        return "<ConstantSet '{0}'>".format(self.id)


class Assignment(Base):
    __tablename__ = 'assignments'

    id = Column(Integer, primary_key=True)
    created = Column(DateTime, default = datetime.datetime.now)
    modified = Column(DateTime, default = datetime.datetime.now, onupdate = datetime.datetime.now)
    constant_set_id = Column('constantSetId', Integer, ForeignKey('constantSets.id'))
    run_range_id = Column('runRangeId',Integer, ForeignKey('runRanges.id'))
    run_range = relationship("RunRange", backref=backref('assignments'))
    variation_id = Column('variationId',Integer, ForeignKey('variations.id'))
    variation = relationship("Variation", backref=backref('assignments'))

    def __repr__(self):
        return "<Assignment '{0}'>".format(self.id)

    def print_deps(self):
        print " ASSIGNMENT: " + repr(self) \
              + " TABLE: " + repr (self.constant_set.type_table)\
              + " RUN RANGE: " + repr(self.run_range)\
              + " VARIATION: " + repr(self.variation)\
              + " SET: " + repr (self.constant_set)
        print "      |"
        print "      +-->" + repr(self.constant_set.vault)


class RunRange(Base):
    __tablename__ = 'runRanges'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    created = Column(DateTime, default = datetime.datetime.now)
    modified = Column(DateTime, default = datetime.datetime.now, onupdate = datetime.datetime.now)
    comment = Column(Text)
    min = Column('runMin',Integer)
    max = Column('runMax',Integer)

    def __repr__(self):
        if self.name != "":
            return "<RunRange {0} {3}:{1}-{2}>".format(self.id, self.min, self.max, self.name)
        else:
            return "<RunRange {0} '{1}-{2}'>".format(self.id, self.min, self.max)



class Variation(Base):
    __tablename__ = 'variations'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    created = Column(DateTime, default = datetime.datetime.now)
    modified = Column(DateTime, default = datetime.datetime.now, onupdate = datetime.datetime.now)
    comment = Column(Text)

    def __repr__(self):
        return "<Variation {0} '{1}'>".format(self.id, self.name)


if __name__=="__main__":
    root_dir = Directory()
    root_dir.path = '/'
    root_dir.name = ''
    root_dir.id = 0

    def structure_dirs(dirs):
        """

        @type dirs: {} dictionary with dir.id as a key
        """
        assert(isinstance(dirs,type({})))

        #clear the full path dictionary
        dirsByFullPath = {root_dir.path: root_dir}

        #begin loop through the directories
        for dir in dirs.values():
            assert (isinstance(dir, Directory))

            parent_dir = root_dir

            # and check if it have parent directory
            if dir.parent_id >0:
                #this directory must have a parent! so now search it
                parent_dir = dirs[dir.parent_id]

            parent_dir.sub_dirs.append(dir)
            dir.path = posixpath.join(parent_dir.path, dir.name)
            dir.parent_dir = parent_dir
            dirsByFullPath[dir.path] = dir

        return dirsByFullPath
        #end of structure_dirs()


    def get_dirs_by_id_dic(dirs):
        result = {}
        for dir in dirs:
            assert(isinstance(dir, Directory))
            result[dir.id]=dir

        return result


    Session = sessionmaker(bind=engine)
    session = Session()
    dirsById = get_dirs_by_id_dic(session.query(Directory))
    dirsByFullPath = structure_dirs(dirsById)


    for key,val in dirsByFullPath.items():
            print key, val, val.id

    experiment_dir = dirsByFullPath['/test/test_vars']

    assert (isinstance(experiment_dir, Directory))

    t = TypeTable()

    for table in experiment_dir.type_tables:
        print " TABLE: " + table.name
        print " +--> COLUMNS:"

        for column in table.columns:
            print "      +-->" + column.name

        print " +--> CONSTANTS:"

        for set in table.constant_sets:
            print "      +-->" + set.vault


    #assignments = session.query(Assignment)

    #for assignment in assignments:
     #   assignment.print_deps()

    query = session.query(Assignment).join(ConstantSet).join(TypeTable).join(RunRange).join(Variation)\
            .filter(Variation.name == "default").filter(TypeTable.name=="test_table").filter(RunRange.min<=1000).filter(RunRange.max>=1000)\
            .order_by(desc(Assignment.id)).limit(1).one()

    print query

    print query.print_deps()

    #for assignment in query:
    #    assignment.print_deps()
    print session.dirty

    q = session.query(Directory)
    q = q.limit(1)

    print q