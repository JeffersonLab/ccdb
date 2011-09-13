
PACKAGES = JANA


CFLAGS += -I$(CCDB_HOME)/include
CXXFLAGS += -I$(CCDB_HOME)/include


MISC_LIBS += -L$(CCDB_HOME)/lib -lccdb 
LD_FLAGS += -L$(CCDB_HOME)/lib -lccdb 
LIBS += -L$(CCDB_HOME)/lib -lccdb 
LD_DIRS += -L$(CCDB_HOME)/lib
LD_LIBS += -lccdb 


include $(HALLD_HOME)/src/BMS/Makefile.shlib
