# ccdb
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




