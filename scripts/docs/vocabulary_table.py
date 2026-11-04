"""The property vocabulary tables of docs/cli.md, generated from ccdb.vocabulary, so the page and the code agree.

    python scripts/docs/vocabulary_table.py --write   # rewrites the part of docs/cli.md between the markers
    python scripts/docs/vocabulary_table.py --check   # exit 1 when the page differs from the code

The part sits between <!-- vocabulary:start --> and <!-- vocabulary:end -->.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, "..", ".."))
PAGE = os.path.join(REPO, "docs", "cli.md")
START, END = "<!-- vocabulary:start -->", "<!-- vocabulary:end -->"


def load_vocabulary():
    """python/ccdb/vocabulary.py by its path: it needs nothing, while importing the ccdb package needs SQLAlchemy,
    which the documentation job does not install"""
    import importlib.util
    spec = importlib.util.spec_from_file_location("ccdb_vocabulary", os.path.join(REPO, "python", "ccdb", "vocabulary.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render():
    vocabulary = load_vocabulary()
    MEANINGS, STANDARD_NAMES = vocabulary.MEANINGS, vocabulary.STANDARD_NAMES

    # owners with the same names share a row
    rows = []
    for owner, names in STANDARD_NAMES.items():
        for row in rows:
            if row[1] == names:
                row[0].append(owner)
                break
        else:
            rows.append(([owner], names))
    lines = ["| owner | names |", "|---|---|"]
    lines += ["| {0} | {1} |".format(", ".join(owners), ", ".join("`{0}`".format(name) for name in names))
              for owners, names in rows]
    lines += ["", "| name | meaning |", "|---|---|"]
    lines += ["| `{0}` | {1} |".format(name, meaning) for name, meaning in MEANINGS.items()]
    return "\n".join(lines)


def replace(text, table):
    if START not in text or END not in text:
        raise SystemExit("{0} has no {1} ... {2} part".format(PAGE, START, END))
    head, rest = text.split(START, 1)
    _, tail = rest.split(END, 1)
    return head + START + "\n" + table + "\n" + END + tail


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    with open(PAGE, encoding="utf-8") as file:
        text = file.read()
    wanted = replace(text, render())
    if args.write:
        with open(PAGE, "w", encoding="utf-8") as file:
            file.write(wanted)
        print("wrote the vocabulary tables of " + PAGE)
    elif wanted != text:
        print("{0}: the vocabulary tables differ from ccdb.vocabulary; run {1} --write".format(PAGE, __file__))
        return 1
    else:
        print("the vocabulary tables of {0} match ccdb.vocabulary".format(PAGE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
