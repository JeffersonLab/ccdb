import logging
import ccdb
import os #for os.linesep
from ccdb import AlchemyProvider
from ccdb.cmd import ConsoleUtilBase
from ccdb.cmd import Theme
from sqlalchemy.orm.exc import NoResultFound

log = logging.getLogger("ccdb.cmd.utils.vers")

#ccdbcmd module interface
def create_util_instance():
    log.debug("      registering AddData")
    return Versions()


#*********************************************************************
#   Class Versions - Show versions of data for specified type table  *
#                                                                    *
#*********************************************************************
class Versions(ConsoleUtilBase):
    """" Show versions of data """
    
    # ccdb utility class descr part 
    #------------------------------
    command = "vers"
    name = "Versions"
    short_descr = "Show versions of data for specified type table"
    uses_db = True

    #variables for each process

    rawentry = "/"   #object path with possible pattern, like /mole/*
    path = "/"       #parent path
    
#----------------------------------------
#   process 
#----------------------------------------  
    def process(self, args):
        log.debug("VersionsUtility is gained a control. {0}\\".format(os.linesep))
        log.debug(" |- arguments : "  + " ".join([("'"+arg+"'") for arg in args]))

        assert self.context is not None
        provider = self.context.provider
        isinstance(provider, AlchemyProvider)
        
        #process arguments
        self.raw_table_path = ""
        self.variation = ""
        self.run = -1
        
        if not self.process_arguments(args):
            return 1
        
        if self.run == -1: 
            self.run = self.context.current_run
            
        if not self.validate():
            return 1
        
        #correct path
        self.table_path = self.context.prepare_path(self.raw_table_path)
        log.debug(" |- prepared path : {0}".format(self.table_path))
        log.debug(" |- run number    : {0}".format(self.run))

        #check such table really exists
        try:
            provider.get_type_table(self.table_path)
        except NoResultFound:
            log.warning("Type table %s not found in the DB", self.table_path)
            return 1
        
        assignments = provider.get_assignments(self.table_path, self.run)
        log.debug(" |- sets found    : {0}".format(len(assignments)))

        print Theme.Directories + "(ID)   (Created)              (Modified)              (variation)     (run range)    (comments)" + Theme.Reset
        for asgmnt in assignments:
            assert isinstance(asgmnt, ccdb.Assignment)
            max_str = repr(asgmnt.run_range.max)
            if asgmnt.run_range.max == ccdb.INFINITE_RUN:
                max_str="inf"
            print " %-5i "%asgmnt.id +\
                  " %-20s"%asgmnt.created.strftime("%Y-%m-%d_%H-%M-%S   ") +\
                  " %-20s"%asgmnt.modified.strftime("%Y-%m-%d_%H-%M-%S   ") +" "+\
                  " %-14s "%asgmnt.variation.name +\
                  " %-25s "%(repr(asgmnt.run_range.min) + "-" + max_str )+\
                  asgmnt.comment[0:20].replace("\n"," ")
        
        return 0
            
#----------------------------------------
#   process_arguments 
#----------------------------------------  
    def process_arguments(self, args):
        
        #parse loop
        i=0

        while i < len(args):
            token = args[i].strip()
            i+=1
            if token.startswith('-'):
                #it is some command, lets parse what is the command

                #variation
                if token == "-v" or token.startswith("--variation"):
                    if i<len(args):
                        self.variation = args[i]
                        i+=1
                                                
                #runrange
                if token == "-r" or token == "--run":
                    try:
                        self.run = int(args[i])
                    except ValueError:
                        log.warning("cannot read run from %s command", token)
                        return False
                
            else:
                #it probably must be a type table path
                self.raw_table_path = token
        
        return True
    
    
#----------------------------------------
#   validate 
#----------------------------------------  
    def validate(self):
        if not self.raw_table_path: return False
        return True

    
#----------------------------------------
#   print_help 
#----------------------------------------
    def print_help(self):
        """Prints help of the command"""
          
        print """Show versions of data for specified type table
        vers /path/to/table
    
    """