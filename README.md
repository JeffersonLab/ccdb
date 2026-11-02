# ccdb

<!-- CI passing badge -->
<a href="https://github.com/JeffersonLab/ccdb/actions"><img src="https://github.com/JeffersonLab/ccdb/actions/workflows/ci.yaml/badge.svg"/></a>

[THE DOCUMENTATION](https://jeffersonlab.github.io/ccdb/#/README)

The Jefferson Lab Calibration Constants Database (CCDB) is a framework to store and manage calibration constants for experiments in high energy and nuclear physics. Primary access to the constants sets is by run number. Constants sets themselves are organized in a tree of constant set types, customized for the experiment and of arbitrary depth. Alternate versions of constants are supported. The complete time history of the constant set tree is kept. Access to alternate versions and to older versions is supported via configuration of the access routines.


CCDB provides readout interfaces for:
* C++
* Python
* Java
* JANA framework
* Command line
* Web site

To manage data (add, update, delete):
* Command line tools ('ccdb' command)
* Python API

Platforms:
* Linux (tested with RedHat, Debian families)
* MacOS
* Windows (partly)

## Installation
The minimum installation to see and manage constants is like this:
```bash
git clone git@github.com:JeffersonLab/ccdb.git ccdb
source ccdb/environment.bash

#That is it! Check it works
ccdb -i
```

The [Installation](https://jeffersonlab.github.io/ccdb/#/get-started/installation) page covers pip, the C++
library with CMake (`find_package(ccdb)`) and a MySQL server.

## Citation

If you use CCDB in your work, please cite it. The citation metadata is in [`CITATION.cff`](CITATION.cff);
GitHub shows it as "Cite this repository" in the sidebar of the repository page, with APA and BibTeX forms.

## License

CCDB is free software under the GNU Lesser General Public License, version 3 or (at your option) any later
version (`LGPL-3.0-or-later`). The LGPL adds permissions to the GNU General Public License version 3, so the
repository carries both texts: the LGPL in [`COPYING.LESSER`](COPYING.LESSER) and the GPL in [`COPYING`](COPYING).
