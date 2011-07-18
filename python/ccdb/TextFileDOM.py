import shlex

class TextFileDOM(object):
    def __init__(self):
        self.comment_lines = []
        self.metas={}
        self.rows=[] #each row should consist of [] - column item
        self.column_names=[]
        self.inconsistant_reason=""
    
    @property
    def data_is_consistant(self):
        self.inconsistant_reason = ""
        if not self.has_data: 
            self.inconsistant_reason = "File has no data"
            return False
        
        columns_length = len(self.rows[0])
        for row in self.rows:
            if len(row) != columns_length: 
                self.inconsistant_reason = "Columns length mistmatch"
                return False
        if len(self.column_names) != columns_length:
            self.inconsistant_reason = "Column names number mistmatch with data colums number"
            return True
        #if we are here, everything is good
        return True
            
    
    @property
    def has_data(self):
        if not len(self.rows): return False
        try:
            if len(self.rows[0]): return True
            else: return False
        except:
            return False
        
            
    
def read_ccdb_text_file(file_name):
    dom = TextFileDOM()    
    try:
        with open(file_name) as f:
            for line in f:
                assert isinstance(line, str)
                
                #prepare line and skip empty one
                line = line.strip()
                if not len(line): continue
                
                
                #what is this line?
                if line.startswith('#meta'):   #comment with meta
                    line = line[5:].strip()
                    if (":" in line) and (line.index(":") != len(line)-1):
                        key = line[:line.index(":")].strip()
                        val = line[line.index(":")+1:].strip()
                        dom.metas[key]=val
                    else:
                        dom.metas[line]=""
                        
                elif line.startswith('#&'):    #comment with column names
                    line = line[2:].strip()
                    dom.column_names = shlex.split(line)
                        
                elif line.startswith("#"):     #comment
                    line = line[1:]
                    dom.comment_lines.append(line)
                    
                else:                          #string with data?
                    tokens = shlex.split(line)
                    values = []
                    for token in tokens:
                        if token.startswith("#"): #stop loop if the comment is met
                            break 
                        else:
                            values.append(token)
                            
                    dom.rows.append(values)
                    
    except IOError as error:
        #error open or read file...
        raise error
    
    #everything is fine?
    return dom
                   