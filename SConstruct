import sys
import os

#Setup default environment. This environment 
if not 'CCDB_HOME' in os.environ:
    print("CCDB_HOME environment variable is not found but should be set to compile the CCDB")
    print("One can run 'source environment.bash' from your bash shell to automatically set environment variables")
    exit(1)

#Create 'default' environment. Other environments will be a copy of this one
default_env = Environment(
    #>> CCDB related default staff <<
    CPPPATH = ['#include', '#src', '#include/SQLite'],
    ENV = os.environ,
)

#Read user flag for using mysql dependencies or not
if ARGUMENTS.get("clang","false")=="true":	
    default_env["CXX"] = "clang++"
    default_env["ENV"]["TERM"]=os.environ["TERM"]

#Export 'default' environment for everything that whishes to use it
Export('default_env')

#Create 'working' environment
default_env.Repository('src')

#Attach SConsctipts
SConscript('src/SQLite/SConscript', 'default_env', variant_dir='tmp/SQLite', duplicate=0)
SConscript('src/Library/SConscript', 'default_env', variant_dir='tmp/Library', duplicate=0)
SConscript('src/Tests/SConscript', 'default_env', variant_dir='tmp/Tests', duplicate=0)

if ARGUMENTS.get("with-examples","false")=="true":
    print("Building with examples. To run example print example_ccdb_<example name> in console")
    SConscript('examples/SConscript', 'default_env', variant_dir='tmp/Examples', duplicate=0)
else:
    print("Building without examples. To build with examples add 'with-examples=true' flag")
    

