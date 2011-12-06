import sys
import os


class CcdbWebInstaller:
    """class that produce installation of ccdb site to target"""

    #ccdb default directory $CCDB_HOME by default 
    ccdb_home = ""

    #Site source directory $CCDB_HOME/web by default 
    web_source_path = ""

    #destination server directory where .html and .php files should be
    dest_html_dir = "" 

    #destination server cgi-bin directory path
    dest_cgi_dir = ""

    #config file for php part
    php_config_file = ""

    #default name for config file for php part
    default_php_config_file = "config.php"

    #config file for cgi part
    cgi_config_file = ""

    #default name for config file for cgi part
    default_cgi_config_file = "ccdb.inp"

    #libccdb.so library full path
    library_file_name = "libccdb.so"

    #copy libccdb.so to destination cgi-bin or not
    # the copying is required if libccdb.so is not in LD_LIBRARY PATH 
    # of the apache server
    copy_library = True
    

#------------------------------------
#   Initialization
#------------------------------------    
    def __init__(self):
        if "CCDB_HOME" in os.environ:
            self.ccdb_home = os.environ["CCDB_HOME"]
            self.web_source_path = os.path.join(self.ccdb_home, "web")
        else:
            print "CCDB_HOME is not set!"

#------------------------------------
#   Instalation
#------------------------------------
    def install(self):
        
        #*** COPY SITE FILES ***
        print "1. Copy html folder"

        all_source = os.path.join(self.web_source_path, "ccdb", "*")
        all_cgi = os.path.join(self.web_source_path, "cgi-bin", "*")

        print all_source
        os.system("cp -rf " + all_source + " " + self.dest_html_dir)
        os.system("cp -rf " + all_cgi + " " + self.dest_cgi_dir)
        
        #*** COPY LIBRARY 
        if self.copy_library:
            print "1.2 Copy libccdb.so"
            full_lib_path = os.path.join(self.ccdb_home,"lib", self.library_file_name)
            os.system("cp -rf " + full_lib_path + " " + self.dest_cgi_dir)

        #*** USE RIGHT CONFIG FILES ***
        print "2. Apply right configs"

        if self.cgi_config_file != self.default_cgi_config_file:
            orig_name = os.path.join(self.dest_cgi_dir, self.cgi_config_file)
            dest_name = os.path.join(self.dest_cgi_dir, self.default_cgi_config_file)
            os.system("mv " + orig_name + " " + dest_name)

        if self.php_config_file != self.default_php_config_file:
            orig_name = os.path.join(self.dest_html_dir, self.php_config_file)
            dest_name = os.path.join(self.dest_html_dir, self.default_php_config_file)
            os.system("mv " + orig_name + " " + dest_name)

        #***  CLEANUP ****
        print "3. Cleanup"
        cgi_pattern = os.path.join(self.dest_cgi_dir,  self.default_cgi_config_file)
        php_pattern = os.path.join(self.dest_html_dir, self.default_php_config_file)

        cgi_pattern = cgi_pattern[:-4] + ".*" + cgi_pattern[-4:]
        php_pattern = php_pattern[:-4] + ".*" + php_pattern[-4:]
        print cgi_pattern
        print php_pattern
        os.system("rm -f " + cgi_pattern)
        os.system("rm -f " + php_pattern)


#------------------------------------
#   Process information
#------------------------------------
    def print_self(self):
        print "Server html directory:"
        print self.dest_html_dir
        print
        print "Server cgi-bin directory:"
        print self.dest_html_dir
        print
        print "Site source directory:"
        print self.web_source_path
        print

