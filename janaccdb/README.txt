This is JANA integration plugin that allows to use CCDB from JANA

Steps to run JANA with CCDB:



PREPARE CCDB
============

1. Install CCDB. Follow the instructions of file install.linux.txt located in 
   the CCDB_HOME directory. 

   (!) Don't forget to setup CCDB in environment in the terminal you are going 
   to run JANA with CCDB in.


2. If you haven't done so, Load HallD database dump to your mysql database

##RUN CODE:

      mysql -u root -p ccdb <$CCDB_HOME/mysql/halld-11-02-2011.mysql.sql


PREPARE JANA
============

1) copy $CCDB_HOME/janaccdb to Jana plugins directory

     cp -r $CCDB_HOME/janaccdb $JANA_HOME/src/plugins


2) modify $JANA_HOME/src/plugins/Makefile, add 'janaccdb' to DIRS string

     nano $JANA_HOME/src/plugins/Makefile
     DIRS := janadot janactl ... janaccdb


3) Rebuild jana JANA 




RUN ANALYSIS
============

1) set JANA_CALIB_URL to your mysql connection

      export JANA_CALIB_URL=mysql://ccdb_user@localhost


2) Now it is possible to run analysis adding --plugin=janaccdb, like:

      hd_root --plugin=cdc_hists --plugin=janaccdb hdgeant_smeared.hddm



MORE DOCUMENTATION
==================

More documentation may be found in $CCDB_HOME/doc directory... with time...
