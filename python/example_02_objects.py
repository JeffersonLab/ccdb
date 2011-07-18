# This example shows how to access directories and type tables
#
# warning(!):
#    set CCDB_CONNECTION variable or 
#    insert connection string in provider.connect()
#    to see this example in action
#
import ccdb
import time

if __name__ == "__main__":
    
    # create provider and connect to database
    provider = ccdb.MySQLProvider()
    if not provider.connect(): exit("Unable to connect to ccdb database")    
    

#---------------------------------------------------
#   D I R E C T O R I E S
#----------------------------------------------------

    # to get a directory by exact name one may use 
    # provider.get_directory("exact_directory_path")
    # the function return ccdb.Directory object or 
    # 'None' if something is wrong (i.e. wrong path)
    
    directory = provider.get_directory("/test")
    
    if not directory: exit("no directory /test found")  #this directory must exist
    assert isinstance(directory, ccdb.Directory)
        
    #directory object have several usefull properties:
    print "directory properties:"
    print "name     :", directory.name        #name of the directory
    print "full_path:", directory.full_path   #full path of the directory
    print "comment  :", directory.comment     #comment of the directory
    
    #creatied and modified time in unix time stamp
    print "\ndirectory times:"
    print time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(directory.created_time)) 
    print time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(directory.modified_time))
    
    #parent directory ling
    print "\nparent directory:  "
    print directory.parent_dir.full_path
    
    #child directories
    print "\nsubdirectories: "
    print "\n".join(["  %s"%sub.name for sub in directory.subdirs])
        