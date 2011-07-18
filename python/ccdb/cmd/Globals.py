import logging
    

def set_verbose(value):
    global verbose
    verbose = value
    
def get_verbose():
    global verbose
    return verbose

def is_debug_verbose():
    global verbose 
    return (verbose>=VerboseModes.Debug)

def is_verbose():
    return (verbose > 0)

class VerboseModes:
    "Like enum with verbose output levels"
    
    No = 0      #No any additional output
    Basic = 1   #Basic additional output
    Debug = 2   #Rich additional output
    
verbose = VerboseModes.No          # if true additional information will be shown

