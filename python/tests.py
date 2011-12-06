from __future__ import with_statement # This isn't required in Python 2.6

import ccdb
import time
import shlex
       
from ccdb import TextFileDOM, read_ccdb_text_file

def test_provider():
    prov = ccdb.MySQLProvider()
    
def test_model():
    import ccdb.MySQLProvider
    print "testing model!"
    variation = ccdb.Variation()
    variation.comment = "ha ha ha"
    print variation.comment


if __name__ == "__main__":

    #test_model()
    dom = read_ccdb_text_file("test.ccdb")
    if not dom: exit("line in exit")
    assert isinstance(dom, TextFileDOM)
    if(dom.data_is_consistant):
        print "metas:"
        for meta, value in dom.metas.items():
            print "    '%s' = '%s'"%(meta,value)
        
        print "columns:"
        print " ".join([name for name in dom.column_names])
        
        print "data:"
        for row in dom.rows:
            assert isinstance(row, list)
            print row
        
        prov = ccdb.MySQLProvider()
        if prov.connect("mysql://ccdb_user@localhost"):
            table = prov.get_type_table("/test/test_vars/test_table", True)
            if table:
                assert isinstance(table, ccdb.ConstantsTypeTable)
                print "len columns ", len(table.columns)
                print "N columns: ", table.ncolumns, " N rows: ", table.nrows
                data = [[1,2,3],[4,5,6]]
                result = prov.create_assignment(dom, "/test/test_vars/test_table", 0, 100, "default", "test assigmnent")
                              
                print "result of adding a constant is... ", result != None
                #print prov.get_assignments("/test/test_vars/test_table", 50)
                assert isinstance(result, ccdb.Assignment)
                print result.raw_data
                print result.data
                print result.data_by_columns
                

                # ------ ACCESS DATA BY COLUMN 
                # one can access the data by [row_num_zero_based]["column name"]
                try:
                    #access to 1-st row, column named "x"
                    print result.data_by_columns[0]["x"] 

                    #access to 2-nd row, column named "x"
                    print result.data_by_columns[1]["x"] 


                except:
                    pass
                
                #assert isinstance(result.data, list)
                
                #print result.type_table.get_column_names()
                #print result.type_table.get_column_types()
                
                assignments = prov.get_assignments("/test/test_vars/test_table", 0)
                for asgmnt in assignments:
                    assert isinstance(asgmnt, ccdb.Assignment)
                    
                    print time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(asgmnt.created_time))
                    print asgmnt.variation.name
                    print asgmnt.type_table.full_path
        
    else:
        print "data was inconsistant"
        print dom.inconsistant_reason
    
    
    
