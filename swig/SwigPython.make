##
## Auto Generated makefile by CodeLite IDE
## any manual changes will be erased      
##
## Debug
ProjectName            :=SwigPython
ConfigurationName      :=Debug
IntermediateDirectory  := $(CCDB_HOME)/tmp
OutDir                 := $(IntermediateDirectory)
WorkspacePath          := "/media/sf_ccdb/ccdb/projects/CodeLite"
ProjectPath            := "/media/sf_ccdb/ccdb/projects/CodeLite"
CurrentFileName        :=
CurrentFilePath        :=
CurrentFileFullPath    :=
User                   :=romanov
Date                   :=01/31/2011
CodeLitePath           :="/home/romanov/.codelite"
LinkerName             :=g++
ArchiveTool            :=ar rcus
SharedObjectLinkerName :=g++ -shared -fPIC
ObjectSuffix           :=.o
DependSuffix           :=.o.d
PreprocessSuffix       :=.o.i
DebugSwitch            :=-gstab
IncludeSwitch          :=-I
LibrarySwitch          :=-l
OutputSwitch           :=-o 
LibraryPathSwitch      :=-L
PreprocessorSwitch     :=-D
SourceSwitch           :=-c 
CompilerName           :=g++
C_CompilerName         :=gcc
OutputFile             :=$(CCDB_HOME)/python/ccdb/ccdb_pyllapi/_ccdb_pyllapi.so
Preprocessors          :=
ObjectSwitch           :=-o 
ArchiveOutputSwitch    := 
PreprocessOnlySwitch   :=-E 
MakeDirCommand         :=mkdir -p
CmpOptions             :=$(shell mysql_config --cflags) $(shell python-config --cflags) -shared -g -fPIC $(Preprocessors)
C_CmpOptions           := -g $(Preprocessors) -fPIC 
LinkOptions            := $(shell mysql_config --libs) $(shell python-config --libs) -shared 
IncludePath            :=  "$(IncludeSwitch)." "$(IncludeSwitch)$(CCDB_HOME)/include" "$(IncludeSwitch)/usr/include/python2.7" "$(IncludeSwitch)." 
RcIncludePath          :=
Libs                   :=$(LibrarySwitch)ccdb 
LibPath                := "$(LibraryPathSwitch)$(CCDB_HOME)/lib" 


##
## User defined environment variables
##
CodeLiteDir:=/usr/share/codelite
Objects=$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(ObjectSuffix) 

##
## Main Build Targets 
##
all: $(OutputFile)

$(OutputFile): makeDirStep $(Objects)
	@$(MakeDirCommand) $(@D)
	$(SharedObjectLinkerName) $(OutputSwitch)$(OutputFile) $(Objects) $(LibPath) $(Libs) $(LinkOptions)
	@echo Executing Post Build commands ...
	cp $(CCDB_HOME)/swig/ccdb_pyllapi.py $(CCDB_HOME)/python/ccdb/ccdb_pyllapi
	@echo Done

makeDirStep:
	@test -d $(IntermediateDirectory) || $(MakeDirCommand) $(IntermediateDirectory)

PreBuild:
	@echo Executing Pre Build commands ...
#	swig -c++ -classic -python $(CCDB_HOME)/swig/ccdb_pyllapi.i
	@echo Done


##
## Objects
##
$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(ObjectSuffix): $(CCDB_HOME)/swig/ccdb_pyllapi_wrap.cxx $(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "$(CCDB_HOME)/swig/ccdb_pyllapi_wrap.cxx" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(DependSuffix): $(CCDB_HOME)/swig/ccdb_pyllapi_wrap.cxx
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(ObjectSuffix) -MF$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(DependSuffix) -MM "$(CCDB_HOME)/swig/ccdb_pyllapi_wrap.cxx"

$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(PreprocessSuffix): $(CCDB_HOME)/swig/ccdb_pyllapi_wrap.cxx
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(PreprocessSuffix) "$(CCDB_HOME)/swig/ccdb_pyllapi_wrap.cxx"


-include $(IntermediateDirectory)/*$(DependSuffix)
##
## Clean
##
clean:
	$(RM) $(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(DependSuffix)
	$(RM) $(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(PreprocessSuffix)
	$(RM) $(OutputFile)


