
SOLIB_NAME = janaccdb.so

ifndef BMSDIR
BMSDIR := ../../../BMS
endif

CXXFLAGS += -I$(CCDB_HOME)/include
LD_FLAGS += -lccdb -L$(CCDB_HOME)
LD_DIRS += -L$(CCDB_HOME)/lib
LD_LIBS += -lccdb


include $(BMSDIR)/Makefile.shlib

