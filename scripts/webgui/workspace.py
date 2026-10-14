"""Where the web GUI check scripts read and write.

Every script takes --space DIR (or the CCDB_SPACE variable): a directory outside version control
(.gitignore lists space-*/) with three subdirectories that the scripts create on first use:

    fixture/   the fixture database ccdb_fixture.sqlite (make_fixture.py)
    reports/   JSON results and server logs (smoke.py, golden.py, browse.py)
    plots/     screenshots (browse.py)

REPO is the repository root, found from this file's location, so the scripts run from any directory.
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE_FILE = "ccdb_fixture.sqlite"


def add_space_argument(parser):
    parser.add_argument("--space", default=os.environ.get("CCDB_SPACE"),
                        help="workspace directory with fixture/, reports/ and plots/ (default: $CCDB_SPACE)")


def resolve(args):
    """The workspace directory from --space or CCDB_SPACE, with its subdirectories in place."""
    if not args.space:
        raise SystemExit("no workspace: pass --space DIR or set CCDB_SPACE")
    space = Path(args.space).resolve()
    for name in ("fixture", "reports", "plots"):
        (space / name).mkdir(parents=True, exist_ok=True)
    return space


def fixture_path(space):
    return space / "fixture" / FIXTURE_FILE


def fixture_url(space):
    return "sqlite:///" + str(fixture_path(space))


def report_name(prefix, phase, label):
    """smoke_phase2_gate.json inside a program run, smoke_ci.json outside one."""
    return f"{prefix}_phase{phase}_{label}.json" if phase is not None else f"{prefix}_{label}.json"
