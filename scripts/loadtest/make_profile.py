#!/usr/bin/env python3
"""The table shapes of a CCDB database, without names, from the JSON of scripts/schema/survey.py.

    python scripts/loadtest/make_profile.py survey.json > scripts/loadtest/profile.json

One entry per CCDB table that holds constants: [rows, columns, sets, mean set bytes, redundant sets], where redundant
sets are the byte-identical copies schema 6 shares (survey --duplicates). make_db.py draws a synthetic database
from it. The shipped profile.json is hallddb's, surveyed read-only on 2026-10-31 (821 431 sets in 679 tables).
"""
import json
import sys


def profile(survey):
    shapes = []
    for table in survey["ccdb_tables"]:
        if not table["sets"]:
            continue
        shapes.append([table["rows"], table["columns"], table["sets"], round(table["bytes"] / table["sets"]),
                       table.get("redundant_sets", 0)])
    shapes.sort()
    return {"source": "scripts/schema/survey.py of {0}, {1}".format(survey["server"]["version"], survey["taken"][:10]),
            "fields": ["rows", "columns", "sets", "mean_set_bytes", "redundant_sets"],
            "tables": shapes}


def main():
    with open(sys.argv[1]) as stream:
        survey = json.load(stream)
    result = profile(survey)
    sys.stdout.write("{\n")
    sys.stdout.write(' "source": {0},\n "fields": {1},\n "tables": [\n'.format(json.dumps(result["source"]), json.dumps(result["fields"])))
    sys.stdout.write(",\n".join("  " + json.dumps(shape) for shape in result["tables"]))
    sys.stdout.write("\n ]\n}\n")


if __name__ == "__main__":
    main()
