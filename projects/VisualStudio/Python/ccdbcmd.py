#python


class ConsoleContext:
    "class to manage console commands"
    def __init__(self):
        pass

    def register_util(self, utility):
        print "Utility registred ", utility.__class__, " \nwhat it do: ", utility.description

#now lets create an instance of this class
context=ConsoleContext()

class ConsoleUtilBase:
    "base class for console utility"
    def __init(self):
        self.description = ""


class HelpUtil(ConsoleUtilBase):
    "gets help"
    description = "help util"
    def __init(self):
        print "hello"
        context.register_util(self)

context.register_util(HelpUtil())
def getContext():
    return context

if __name__ == "__main__":
    print "main is main!"
import ccdb
import ccdb.cmd
ccdb.haha()
import re
preg="(?P<times>^[0-9])*(?P<type>[0-9a-zA-Z_]+)(\\((?P<name>.*)\\))*";
m = re.match(preg, "5hereSpec(45)")
print m.groups()

if(m.group("times")):
	print "num times ",m.group("times")
if(m.group("type")):
	print "num type ",m.group("type")
if(m.group("name")):
	print "num name ",m.group("name")
	x = 5;
	y = 5 + m.group("name")
	print y
m = re.match(preg, "hereSpec")
print m.groups()

print "success"