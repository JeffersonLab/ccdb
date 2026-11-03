# ccdb

<!-- CI passing badge -->
<a href="https://github.com/JeffersonLab/ccdb/actions"><img src="https://github.com/JeffersonLab/ccdb/actions/workflows/python-tests.yml/badge.svg"/></a> <a href="https://github.com/JeffersonLab/ccdb/actions"><img src="https://github.com/JeffersonLab/ccdb/actions/workflows/cpp-tests.yml/badge.svg"/></a>

[THE DOCUMENTATION](https://jeffersonlab.github.io/ccdb/)

The Jefferson Lab Calibration Constants Database (CCDB) stores and serves the calibration constants that the
reconstruction of a detector's data needs: typed tables addressed by path, valid for run ranges, with branches
(variations, with inheritance), named campaign snapshots (tags) and the complete history of every change. A new
version supersedes the old one, which stays readable; every version records who added it, when (a UTC instant to the
microsecond) and why, and identical data is stored once, named by its SHA-256.

CCDB serves the constants through:
* C++ (MySQL, SQLite, and `http(s)://` connection strings that read run bundles through the HTTP API)
* Python, with Parquet export and pandas/polars data frames
* the JANA2 service `CCDB_service` and DD4hep plugins
* an HTTP API with cacheable run bundles, and a read-only MCP server for AI agents
* the `ccdb` command line and a web GUI

To manage data (add, tag, deprecate, describe):
* Command line tools ('ccdb' command)
* Python API

Platforms:
* Linux (tested with RedHat, Debian families)
* macOS
* Windows (Python)

## Installation

```bash
python -m pip install ccdb
```

gives the library and the `ccdb` command. Extras: `ccdb[web]` (web GUI), `ccdb[api]` (HTTP API),
`ccdb[mcp]` (MCP server, Python 3.10+), `ccdb[export]` (Parquet), `ccdb[frames]` (pandas frames).
From a checkout, `source environment.bash` puts the checkout's `ccdb` on the path.

CCDB 2.5 works with database schema 6. A database made by 2.4 is upgraded once, with a dry run and a rollback:
[Upgrading to CCDB 2.5](https://jeffersonlab.github.io/ccdb/#/deployment/upgrade-2.5).

The [Installation](https://jeffersonlab.github.io/ccdb/#/get-started/installation) page covers pip, the C++
library with CMake (`find_package(ccdb)`) and a MySQL server.

## Citation

If you use CCDB in your work, please cite it. The citation metadata is in [`CITATION.cff`](CITATION.cff);
GitHub shows it as "Cite this repository" in the sidebar of the repository page, with APA and BibTeX forms.

## License

CCDB is free software under the GNU Lesser General Public License, version 3 or (at your option) any later
version (`LGPL-3.0-or-later`). The LGPL adds permissions to the GNU General Public License version 3, so the
repository carries both texts: the LGPL in [`COPYING.LESSER`](COPYING.LESSER) and the GPL in [`COPYING`](COPYING).
