#! /usr/bin/python

import os
import stat
import re 

def search_calib_function(line):
    #preg = "->Get.*\\\((?P<quantity>^[0-9]*)(?P<name>[0-9a-zA-Z_]+)*(=(?P<type>.*))*"
        #if self.no_columns_quantity:
         #   preg = "(?P<name>[0-9a-zA-Z_]+)*(=(?P<type>.*))*"
    try:
        preg = '^.*>Get(Calib)*\\((?P<namepath>[\w/"]+),\s*(?P<variable>[0-9a-zA-Z_]+)(,.*)*\\)' #\\\((?P<namepath>^.+),(?P<variable>[0-9a-zA-Z_]+)\\\)'
       
        m = re.match(preg, line)
    
        if not m: 
            return None
        #print line
        result={}

        if m.group("namepath") and m.group("variable"):
            return (m.group("namepath"), m.group("variable"))

    except Exception as ex:
        print ex
        
    return None


#--- constants ----

file_extensions = [".c",".cc", ".cxx", ".cpp", ".h", ".hxx", ".hpp", ".xml"]

def check_name(name):
    lowname = name.lower()
    for ext in file_extensions:
        if lowname.endswith(ext): return True
    return False
    

dirs_to_search = [x[0] for x in os.walk('d:\\Projects\\Share\\gluex\\sim-recon\\trunk\\src') if not ".svn" in x[0]]
files_to_process = []
for dir_to_search in dirs_to_search:
    files_to_process.extend([
                             os.path.join(dir_to_search,name) 
                             for name in os.listdir(dir_to_search)
                             if check_name(name)
                             ])

report = ""
print "SEARCHING {} files in {} directories".format(len(files_to_process), len(dirs_to_search))
for file in files_to_process:
    try:
        line_num = 0
        founds=[]
        for line in open(file):
            line_num += 1
            result=search_calib_function(line)
            if result:
                (namepath,variable) = result
                founds.append( (line_num,line,namepath,variable) )

        for founding in founds:
            (line_num,line,namepath,variable) = founding
            report+=os.linesep
            report+="======================================================================="+os.linesep
            report+= "FILE: " + file + " LINE(" + repr(line_num)+") : " + os.linesep + line.replace(" ","").replace("\t","")
            report+= "namepath: "+namepath+ " variable: " + variable + os.linesep
            if not namepath.startswith('"'):
                report+= " Namepath is given by variable. Looking for variable: " +namepath+ os.linesep
                sub_line_num=0
                for line in open(file):
                    sub_line_num+=1
                    if namepath in line:
                        report+= " LINE(" + repr(sub_line_num)+") : " + line.replace(" ","").replace("\t","")
                report+=os.linesep

            report+= "Looking for variable: " + variable + os.linesep
            sub_line_num=0
            for line in open(file):
                sub_line_num+=1
                if variable in line:
                    report+= " LINE(" + repr(sub_line_num)+") : " + line.replace(" ","").replace("\t","")
                
            
    except:
        pass

print report