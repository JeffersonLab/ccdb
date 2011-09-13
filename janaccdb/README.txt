This is JANA integration plugin that allows to use CCDB from JANA

Steps to run JANA with CCDB:



PREPARE CCDB
============

To run JANA with ccdb one should:

1. Install CCDB. Follow the instructions of file install.linux.txt 
   located in the CCDB_HOME directory. 

   Don't forget to setup CCDB in environment
   in the terminal where are you going to run JANA with CCDB.


2. Load database dump to your mysql database

## RUN CODE:

    mysql -u ccdb_user < ccdb_calib_dump.mysql


3) test everything is ready 

## RUN CODE:
    
    ccdbcmd ls --dump-tree

This command will print a directory tree as a test.
    


PREPARE JANA
============

1) copy $CCDB_HOME/janaccdb to Jana plugins directory

     cp $CCDB_HOME/janaccdb $JANA_HOME/src/plugins


2) modify $JANA_HOME/src/plugins/Makefile, add 'janaccdb' to DIRS string

     nano $CCDB_HOME/src/plugins/Makefile
     DIRS := janadot janactl ... janaccdb


3) make JANA 




RUN ANALYSIS
============

1) set JANA_CALIB_URL to your mysql connection

      export JANA_CALIB_URL=mysql://ccdb_user@localhost


2) Now it is possible to run analysis adding --plugin=janaccdb, like:

      hd_root --plugin=phys_tree --plugin=janaccdb hdgeant_smeared.hddm



MORE DOCUMENTATION
==================

More documentation may be found in $CCDB_HOME/doc directory... with time...
