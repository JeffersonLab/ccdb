from __future__ import print_function

import shlex

__all__ = ["TextFileDOM"]

META_FULL_REQUEST = 'full request'
META_VARIATION = 'variation'
META_CREATED = 'created'
META_RUN_RANGE = 'run range'
META_AUTHOR = 'author'


# *********************************************************************
#   Class TextFileDOM - store information of text data files         *
#                                                                    *
# *********************************************************************
class TextFileDOM(object):
    """store information of text data files"""

    def __init__(self):
        self.comment_lines = []
        self.metas = {}
        self.rows = []  # each row should consist of [] - column item
        self.column_names = []
        self.inconsistent_reason = ""

    @property
    def data_is_consistent(self):
        self.inconsistent_reason = ""
        if not self.has_data:
            self.inconsistent_reason = "File has no data"
            return False

        for row_index, row in enumerate(self.rows):
            if len(row) != self.columns_length:
                self.inconsistent_reason = "Row length mismatch. " \
                                           "Row '{0}' has '{1}' values while awaited number of columns is '{2}'". \
                    format(row_index, len(row), self.columns_length)
                return False

        if len(self.column_names) != self.columns_length:
            self.inconsistent_reason = "Column names number is: '{0}'. It is not equal to data columns number: '{1}'". \
                format(len(self.column_names), self.columns_length)
            return True
        # if we are here, everything is good
        return True

    @property
    def columns_length(self):
        """returns number of columns based on row[0] length
        return 0 if there is no data
        """
        if not len(self.rows):
            return 0

        # now we know there is at least 1 row
        return len(self.rows[0])

    @property
    def has_data(self):
        if not len(self.rows):
            return False

        try:
            if len(self.rows[0]):
                return True
        except IndexError:
            pass
        return False


# ----------------------------------------
#   read_ccdb_text_file
# ----------------------------------------
def read_ccdb_text_file(file_name):
    dom = TextFileDOM()
    try:
        with open(file_name) as f:
            for line in f:
                assert isinstance(line, str)

                # prepare line and skip empty one
                line = line.strip()
                if not len(line):
                    continue

                # what is this line?
                if line.startswith('#meta'):  # comment with meta
                    line = line[5:].strip()
                    if (":" in line) and (line.index(":") != len(line) - 1):
                        key = line[:line.index(":")].strip()
                        val = line[line.index(":") + 1:].strip()
                        dom.metas[key] = val
                    else:
                        dom.metas[line] = ""

                elif line.startswith('#&'):  # comment with column names
                    line = line[2:].strip()
                    dom.column_names = shlex.split(line)

                elif line.startswith("#"):  # comment
                    line = line[1:]
                    dom.comment_lines.append(line)

                else:  # string with data?
                    tokens = shlex.split(line)
                    values = []
                    for token in tokens:
                        if token.startswith("#"):  # stop loop if the comment is met
                            break
                        else:
                            values.append(token)

                    dom.rows.append(values)

    except IOError as error:
        # error open or read file...
        raise error

    # everything is fine?
    return dom


# ----------------------------------------
#   read_namevalue_text_file
# ----------------------------------------
def read_namevalue_text_file(file_name, replace_c_comments=False):
    """
    :param replace_c_comments: - if file contains // - 'C' style comments, replace them by # first
    :type replace_c_comments: bool
    :param file_name: Name of file to read
    """
    dom = TextFileDOM()
    try:
        with open(file_name) as f:
            values = []
            for line in f:
                assert isinstance(line, str)

                # prepare line and skip empty one
                line = line.strip()
                if replace_c_comments:
                    line = line.replace("//", "#")
                if not line:
                    continue

                # what is this line?
                if line.startswith("#"):  # comment
                    line = line[1:]
                    dom.comment_lines.append(line)

                else:  # string with data?
                    tokens = shlex.split(line)

                    # check we have name and value
                    if len(tokens) < 2:
                        print("ERROR. The name-value file have less than 2 columns. So where are names and values?")
                        raise IOError()
                    values.append(tokens[1])
                    dom.column_names.append(tokens[0])

            # add line
            dom.rows.append(values)

    except IOError as error:
        # error open or read file...
        raise error

    # everything is fine?
    return dom
