##
## Auto Generated makefile by CodeLite IDE
## any manual changes will be erased      
##
## Debug
ProjectName            :=WebCgi
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
OutputFile             :=$(WorkspacePath)/../../bin/ccdb.cgi
Preprocessors          :=
ObjectSwitch           :=-o 
ArchiveOutputSwitch    := 
PreprocessOnlySwitch   :=-E 
ObjectsFileList        :="/media/sf_ccdb/projects/CodeLite/WebCgi.txt"
MakeDirCommand         :=mkdir -p
CmpOptions             :=$(shell mysql_config --cflags) -fPIC -g  $(Preprocessors)
C_CmpOptions           := -g  $(Preprocessors)
LinkOptions            :=  
IncludePath            :=  $(IncludeSwitch). $(IncludeSwitch)$(WorkspacePath)/../../include 
RcIncludePath          :=
Libs                   :=$(LibrarySwitch)ccdb 
LibPath                := $(LibraryPathSwitch). $(LibraryPathSwitch)"$(shell mysql_config --libs)" $(LibraryPathSwitch)$(WorkspacePath)/../../lib 


##
## User defined environment variables
##
CodeLiteDir:=/usr/share/codelite
Objects=$(IntermediateDirectory)/src_mainWeb$(ObjectSuffix) 

##
## Main Build Targets 
##
all: $(OutputFile)

$(OutputFile): makeDirStep $(Objects)
	@$(MakeDirCommand) $(@D)
	$(LinkerName) $(OutputSwitch)$(OutputFile) $(Objects) $(LibPath) $(Libs) $(LinkOptions)

objects_file:
	@echo $(Objects) > $(ObjectsFileList)

makeDirStep:
	@test -d ./Debug || $(MakeDirCommand) ./Debug

PreBuild:


##
## Objects
##
$(IntermediateDirectory)/src_mainWeb$(ObjectSuffix): ../../src/mainWeb.cc $(IntermediateDirectory)/src_mainWeb$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/mainWeb.cc" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/src_mainWeb$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/src_mainWeb$(DependSuffix): ../../src/mainWeb.cc
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/src_mainWeb$(ObjectSuffix) -MF$(IntermediateDirectory)/src_mainWeb$(DependSuffix) -MM "/media/sf_ccdb/src/mainWeb.cc"

$(IntermediateDirectory)/src_mainWeb$(PreprocessSuffix): ../../src/mainWeb.cc
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/src_mainWeb$(PreprocessSuffix) "/media/sf_ccdb/src/mainWeb.cc"


-include $(IntermediateDirectory)/*$(DependSuffix)
##
## Clean
##
clean:
	$(RM) $(IntermediateDirectory)/src_mainWeb$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/src_mainWeb$(DependSuffix)
	$(RM) $(IntermediateDirectory)/src_mainWeb$(PreprocessSuffix)
	$(RM) $(OutputFile)


