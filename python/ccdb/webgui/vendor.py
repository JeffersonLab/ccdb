"""Fetches the vendored browser libraries into static/vendor/ and checks them against a sha256 manifest.

Usage:
    python -m ccdb.webgui.vendor          # verify (and fetch what is missing)
    python -m ccdb.webgui.vendor --fetch  # fetch everything again and verify

The wheel ships static/, so a server on the lab network runs with no CDN access. The manifest pins
the exact bytes: a library upgrade means editing VENDORED below, running --fetch, checking the new
hashes in, and reviewing the diff. A hash mismatch is an error, never auto-corrected.
"""
import argparse
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

STATIC = Path(__file__).resolve().parent / "static"
VENDOR_DIR = STATIC / "vendor"
MANIFEST = VENDOR_DIR / "MANIFEST.json"

BOOTSTRAP_VERSION = "5.3.8"
VENDORED = {
    # relative path under static/vendor/ -> source URL (jsDelivr serves the npm dist files unchanged)
    f"bootstrap-{BOOTSTRAP_VERSION}/bootstrap.min.css": f"https://cdn.jsdelivr.net/npm/bootstrap@{BOOTSTRAP_VERSION}/dist/css/bootstrap.min.css",
    f"bootstrap-{BOOTSTRAP_VERSION}/bootstrap.bundle.min.js": f"https://cdn.jsdelivr.net/npm/bootstrap@{BOOTSTRAP_VERSION}/dist/js/bootstrap.bundle.min.js",
    f"bootstrap-{BOOTSTRAP_VERSION}/LICENSE": f"https://cdn.jsdelivr.net/npm/bootstrap@{BOOTSTRAP_VERSION}/LICENSE",
}


def sha256_of(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(relative, url):
    target = VENDOR_DIR / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as response:
        target.write_bytes(response.read())
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fetch", action="store_true", help="download every file again before verifying")
    parser.add_argument("--write-manifest", action="store_true", help="record the hashes of the files on disk (after a reviewed upgrade)")
    args = parser.parse_args()

    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    problems = []
    for relative, url in VENDORED.items():
        target = VENDOR_DIR / relative
        if args.fetch or not target.exists():
            print(f"fetch {url}")
            fetch(relative, url)
        digest = sha256_of(target)
        if args.write_manifest or relative not in manifest:
            manifest[relative] = digest
            print(f"record {relative} {digest[:12]}…")
        elif manifest[relative] != digest:
            problems.append(f"{relative}: sha256 {digest[:12]}… differs from the manifest {manifest[relative][:12]}…")
        else:
            print(f"ok     {relative}")
    stale = sorted(set(manifest) - set(VENDORED))
    if stale:
        problems.append("manifest entries without a VENDORED source: " + ", ".join(stale))
    MANIFEST.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n")
    for problem in problems:
        print("ERROR", problem, file=sys.stderr)
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
