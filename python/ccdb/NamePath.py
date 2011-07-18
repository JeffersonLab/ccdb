import posixpath

def split(path):
    return posixpath.split(path)

class PathObject():
    
    def __init__(self):
        self.name = ""
        self.path = ""
        self.CCDBType = "Directory"
        self.tag = None
        
class PathObjectType:
    Directory = "Directory"
    TypeTable = "TypeTable"
    Variation = "Variation"
    Run = "Run"