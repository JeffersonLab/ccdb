# Copyright Spack Project Developers. See COPYRIGHT file for details.
#
# SPDX-License-Identifier: (Apache-2.0 OR MIT)

from spack_repo.builtin.build_systems.cmake import CMakePackage

from spack.package import *


class Ccdb(CMakePackage):
    """CCDB, the Calibration Constants Database: calibration constants of nuclear and high
    energy physics experiments, looked up by run number in a tree of tables, with variations,
    the full history of every change and named snapshot tags. This package builds the C++
    library; the Python library and the ccdb command are on PyPI as ccdb."""

    homepage = "https://jeffersonlab.github.io/ccdb"
    url = "https://github.com/JeffersonLab/ccdb/archive/refs/tags/v2.4.0.tar.gz"
    git = "https://github.com/JeffersonLab/ccdb.git"

    maintainers("DraTeots")

    license("GPL-2.0-or-later")

    version("main", branch="v2-main")
    version("2.4.0", sha256="eca1a3777a63c7eb1ebc777249dbb48e798d47a1e9e0cb038068d11d991dfaa2")

    # The CMake project of the C++ library is in the cpp directory of the repository
    root_cmakelists_dir = "cpp"

    variant("mysql", default=True, description="MySQL and MariaDB provider (mysql:// connections)")
    # The components of the CCDB 2.5 program; each variant gains its dependencies and its CMake
    # option in the release that brings the component, and is refused until then.
    variant("http", default=False, description="HTTP provider that reads through the CCDB API")
    variant("jana2", default=False, description="JANA2 service CCDB_service and its plugin")
    variant("dd4hep", default=False, description="DD4hep conditions loader and constants plugin")
    conflicts("+http", msg="the HTTP provider is not part of this version of CCDB yet")
    conflicts("+jana2", msg="the JANA2 service is not part of this version of CCDB yet")
    conflicts("+dd4hep", msg="the DD4hep plugins are not part of this version of CCDB yet")

    depends_on("c", type="build")
    depends_on("cxx", type="build")
    depends_on("cmake@3.16:", type="build")

    depends_on("sqlite@3:")
    depends_on("mysql-client", when="+mysql")

    def cmake_args(self):
        args = [
            # FindMySQL picks up any client library on the system; without +mysql it must not
            self.define("CMAKE_DISABLE_FIND_PACKAGE_MySQL", self.spec.satisfies("~mysql"))
        ]
        if self.spec.satisfies("@2.5:"):
            # The Catch2 suite and its install to bin; 2.4 always builds it
            args.append(self.define("CCDB_BUILD_TESTS", self.run_tests))
        return args
