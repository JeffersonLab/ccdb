# It is assumed that by default the site is lying in /var/www/
# and cgi directory is in 'site/cgi-bin' and html is is 'site/html'

import ccdb_web_installer
import os


if __name__ == "__main__":
    installer = ccdb_web_installer.CcdbWebInstaller()
    
    #directory where all .php, .html and other contet files are
    installer.dest_html_dir = "/group/halld/www/halldweb1/html/ccdb/"


    #directory where cgi part is 
    installer.dest_cgi_dir = "/group/halld/www/halldweb1/htbin/ccdb"
    

    #config file for php part
    #should be config.<something>.php
    installer.php_config_file = "config.ifarml64.php"


    #config file for cgi part
    #should be ccdb.<something>.inp
    installer.cgi_config_file = "ccdb.ifarml64.inp"
    
        
    # the copying libccdb.so to destination cgi-bin is
    # required if libccdb.so is not in LD_LIBRARY PATH 
    # of the apache server
    installer.copy_library = True

    #INSTALLATION
    installer.print_self()
    installer.install()

