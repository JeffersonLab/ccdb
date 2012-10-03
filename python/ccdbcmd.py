#python

def parse_columns(value):
    import re
    
    print "\n----------------------"
    print value
    print "----------------------\n  "
    
    
    preg="(?P<times>^[0-9]*)(\\((?P<pretype>.*)\\))*(?P<name>[0-9a-zA-Z_]+)*(\\((?P<type>.*)\\))*";
    m = re.match(preg, value)
    print m.groups()


        
    if(m.group("times")):
        print "num times ",m.group("times")
        
    if(m.group("pretype")):
        print "num pretype ",m.group("pretype")
        
    if(m.group("type")):
        print "num type ",m.group("type")
        
    if(m.group("name")):
        print "num name ",m.group("name")

def test_parse_columns():
    parse_columns("x")
    parse_columns("10x")
    parse_columns("x(int)")
    parse_columns("10x(int)")
    parse_columns("10(int)x")
    parse_columns("10(int)")
    parse_columns("(int)")

if __name__ == "__main__":

    import ccdb
    #import ccdb.ccdb_pyllapi
    ccdb.init_ccdb_console()
