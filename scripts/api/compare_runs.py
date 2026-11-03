"""Compares two API smoke reports URL by URL: status and bytes must be equal.

    python scripts/api/compare_runs.py <reference.json> <other.json>

The container job of api-tests.yml runs the suite in-process and through nginx and compares the two, so the image and
the cache serve what the code serves. Bundle files are compared by status only: a file built twice differs in its
log record's time.
"""
import json
import sys


def main():
    reference, other = (json.load(open(path)) for path in sys.argv[1:3])
    other_by_url = {each["url"]: each for each in other["results"]}
    differences = []
    for each in reference["results"]:
        theirs = other_by_url.get(each["url"])
        if theirs is None:
            differences.append((each["label"], "missing"))
        elif theirs["status"] != each["status"]:
            differences.append((each["label"], "status {0} != {1}".format(theirs["status"], each["status"])))
        elif each["kind"] != "file" and theirs["bytes"] != each["bytes"] and each["label"] not in ("health",):
            differences.append((each["label"], "bytes {0} != {1}".format(theirs["bytes"], each["bytes"])))
    for label, why in differences:
        print("DIFFERS {0}: {1}".format(label, why))
    print("{0} URLs, {1} differ".format(len(reference["results"]), len(differences)))
    sys.exit(1 if differences else 0)


if __name__ == "__main__":
    main()
