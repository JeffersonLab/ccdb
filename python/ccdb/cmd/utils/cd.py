from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd.Theme import Theme
from ccdb.cmd import is_verbose, is_debug_verbose
from ccdb.ccdb_pyllapi import Directory
import posixpath

def create_util_instance():
    if is_debug_verbose(): print "      registring ChangeDir"
    return ChangeDir()

class ChangeDir(ConsoleUtilBase):
    command = "cd"
    name = "ChangeDir"
    short_descr = "Change current directory"
    uses_db = True
    
    #variables for each process
    rawentry = "/"       #object path with possible pattern, like /mole/*
    
    def print_help(ChangeDir):
        print """ Change current directory """ 
    # ---- end of print_help() ----


    def process(self, args):
        if(is_debug_verbose()):
            print "ChangeDir is gained a control over the process."
            print " ".join(args)
        
        if len(args):
            self.rawentry = args[0]
        
            #correct ending /
            if self.rawentry.endswith("/"):
                self.rawentry = self.rawentry[:-1]
        else:
            self.rawentry= "/"
         
       
        
        #local or absolute path?
        if not self.rawentry.startswith("/"):
            self.rawentry = posixpath.join(self.context.current_path , self.rawentry)
        
        #normalize
        self.rawentry = posixpath.normpath(self.rawentry)

        #try to find the directory
        directory = self.context.provider.get_directory(self.rawentry)
        if directory:
            self.context.current_path = self.rawentry
            #print self.rawentry
        else:
            print "Can't find the directory"
            