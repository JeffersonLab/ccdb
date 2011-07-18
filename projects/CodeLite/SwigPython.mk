##
## Auto Generated makefile by CodeLite IDE
## any manual changes will be erased      
##
## Debug
ProjectName            :=SwigPython
ConfigurationName      :=Debug
IntermediateDirectory  :=./Debug
OutDir                 := $(IntermediateDirectory)
WorkspacePath          := "/media/sf_ccdb/projects/CodeLite"
ProjectPath            := "/media/sf_ccdb/projects/CodeLite"
CurrentFileName        :=
CurrentFilePath        :=
CurrentFileFullPath    :=
User                   :=root
Date                   :=06/24/2011
CodeLitePath           :="/root/.codelite"
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
OutputFile             :=$(WorkspacePath)/../../python/ccdb/ccdb_pyllapi/_ccdb_pyllapi.so
Preprocessors          :=
ObjectSwitch           :=-o 
ArchiveOutputSwitch    := 
PreprocessOnlySwitch   :=-E 
ObjectsFileList        :="/media/sf_ccdb/projects/CodeLite/SwigPython.txt"
MakeDirCommand         :=mkdir -p
CmpOptions             :=$(shell mysql_config --cflags) $(shell python-config --cflags) -shared -g $(Preprocessors)
C_CmpOptions           := -g $(Preprocessors)
LinkOptions            := $(shell mysql_config --libs) $(shell python-config --libs) -shared 
IncludePath            :=  $(IncludeSwitch). $(IncludeSwitch)$(WorkspacePath)/../../include $(IncludeSwitch)/usr/include/python2.7 $(IncludeSwitch). 
RcIncludePath          :=
Libs                   :=$(LibrarySwitch)ccdb 
LibPath                := $(LibraryPathSwitch)$(WorkspacePath)/../../lib 


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
	cp $(WorkspacePath)/../../swig/ccdb_pyllapi.py $(WorkspacePath)/../../python/ccdb/ccdb_pyllapi
	@echo Done

objects_file:
	@echo $(Objects) > $(ObjectsFileList)

makeDirStep:
	@test -d ./Debug || $(MakeDirCommand) ./Debug

PreBuild:
	@echo Executing Pre Build commands ...
	swig -c++ -python $(WorkspacePath)/../../swig/ccdb_pyllapi.i
	@echo Done


##
## Objects
##
$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(ObjectSuffix): ../../swig/ccdb_pyllapi_wrap.cxx $(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/swig/ccdb_pyllapi_wrap.cxx" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(DependSuffix): ../../swig/ccdb_pyllapi_wrap.cxx
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(ObjectSuffix) -MF$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(DependSuffix) -MM "/media/sf_ccdb/swig/ccdb_pyllapi_wrap.cxx"

$(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(PreprocessSuffix): ../../swig/ccdb_pyllapi_wrap.cxx
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(PreprocessSuffix) "/media/sf_ccdb/swig/ccdb_pyllapi_wrap.cxx"


-include $(IntermediateDirectory)/*$(DependSuffix)
##
## Clean
##
clean:
	$(RM) $(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(DependSuffix)
	$(RM) $(IntermediateDirectory)/swig_ccdb_pyllapi_wrap$(PreprocessSuffix)
	$(RM) $(OutputFile)


