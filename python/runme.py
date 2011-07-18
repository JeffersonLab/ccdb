# file: runme.py

# This file illustrates the proxy class C++ interface generated
# by SWIG.

import ccdb.ccdb_pyllapi

run_range = ccdb.ccdb_pyllapi.DRunRange()
print run_range.GetId()
#run_range.Get
print "my soul!"


"""
import ccdb_python
import inspect

# ----- Run range checks -----
b = ccdb_python.DRunRange();
b.SetMax(400);
b.SetMin(10);
print "\n max: ", b.GetMax()," min ", b.GetMin();
print b


# ----- DDirectory checks -----

print "Checking DDirectory"
dir=ccdb_python.DDirectory()
dir.SetId(5)
print dir.GetId()
print dir.GetSubdirectories()

# ----- DDataProvider -----

prov = ccdb_python.DMySQLDataProvider();
if prov.Connect("mysql://root:MnogonOjekU40nojek!@localhost"):
    print "wow! We connected!"
    dir = prov.GetDirectory("/test")
    if(dir):
        print "found directory /test"
        print dir
        print dir.GetFullPath()
        print dir.GetParentDirectory()
        subDirs = dir.GetSubdirectories()
        print subDirs.size()
        for i in range(0,subDirs.size()):
            print subDirs[i].GetName()

    if(prov.GetDirectory("hren")):
        print "found it!"
    else: print "not found"

else:
    print "ohhh ono!! We are not!"

print "Goodbye"

"""
