"""Constants as data frames, for analysis (docs/apis/python.md#data-frames).

    from ccdb import AlchemyProvider
    from ccdb.frames import to_dataframe

    provider = AlchemyProvider()
    provider.connect("sqlite:////path/ccdb.sqlite")
    frame = to_dataframe(provider, "/epic/HCal/adc_calib:1500")           # pandas, needs the frames extra
    frame.attrs["units"]["sampFrac"]                                      # the column's units ('' when none)
    frame = to_dataframe(provider, "/epic/HCal/adc_calib:1500", library="polars")

The request is a CCDB request string (/path:run:variation:time or /path:run@tag) resolved as `ccdb cat` resolves
it. Columns take the table's types: int and long as int64, uint and ulong as uint64, double as float64, bool as
bool, string as text. A pandas frame carries the units in attrs["units"], the column comments in attrs["comments"],
and the table path and the assignment (id, run range, variation, UTC creation time, author, comment, sha256) in
attrs["table"] and attrs["assignment"]; a polars frame has no attributes, so column_units(table) gives them.
"""
import datetime

from ccdb.path_utils import local_to_utc

# CCDB column type -> (pandas dtype, polars type name)
COLUMN_TYPES = {"int": ("int64", "Int64"), "long": ("int64", "Int64"), "uint": ("uint64", "UInt64"),
                "ulong": ("uint64", "UInt64"), "double": ("float64", "Float64"), "bool": ("bool", "Boolean"),
                "string": ("object", "Utf8")}


def typed_value(text, column_type):
    """A cell's text as the Python value of its column type"""
    if column_type in ("int", "long", "uint", "ulong"):
        return int(text)
    if column_type == "double":
        return float(text)
    if column_type == "bool":
        return text.strip().lower() in ("1", "true", "yes")
    return text


def utc_created(assignment):
    """The creation time of an assignment as an aware UTC datetime"""
    created = assignment.created
    if created.tzinfo is None:
        return local_to_utc(created)
    return created.astimezone(datetime.timezone.utc)


def assignment_metadata(assignment):
    """The fields that name an assignment, for frames and exports"""
    return {"id": assignment.id, "run_min": assignment.run_range.min, "run_max": assignment.run_range.max,
            "variation": assignment.variation.name, "created": utc_created(assignment),
            "author": assignment.author.name if assignment.author else "", "comment": assignment.comment or "",
            "sha256": assignment.constant_set.sha256}


def column_units(table):
    """{column name: units ('' when none)} of a TypeTable"""
    return {column.name: column.units or "" for column in table.columns}


def typed_columns(assignment):
    """[(name, CCDB type, [values])] of an assignment's data, in the table's column order"""
    table = assignment.constant_set.type_table
    rows = assignment.constant_set.data_table
    return [(column.name, column.type, [typed_value(row[index], column.type) for row in rows])
            for index, column in enumerate(table.columns)]


def to_dataframe(provider, request, library="pandas"):
    """The data of the assignment a request names, as a pandas (default) or polars data frame"""
    assignment = provider.get_assignment_by_request(request)
    table = assignment.constant_set.type_table
    columns = typed_columns(assignment)
    if library == "polars":
        import polars
        return polars.DataFrame({name: polars.Series(name, values, dtype=getattr(polars, COLUMN_TYPES[kind][1]))
                                 for name, kind, values in columns})
    if library != "pandas":
        raise ValueError("library is 'pandas' or 'polars', not '{0}'".format(library))
    import pandas
    frame = pandas.DataFrame({name: pandas.Series(values, dtype=COLUMN_TYPES[kind][0]) for name, kind, values in columns})
    frame.attrs["table"] = table.path
    frame.attrs["units"] = column_units(table)
    frame.attrs["comments"] = {column.name: column.comment or "" for column in table.columns}
    frame.attrs["assignment"] = assignment_metadata(assignment)
    return frame
