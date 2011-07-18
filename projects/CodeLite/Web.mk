##
## Auto Generated makefile by CodeLite IDE
## any manual changes will be erased      
##
## Debug
ProjectName            :=Web
ConfigurationName      :=Debug
IntermediateDirectory  :=./Debug
OutDir                 := $(IntermediateDirectory)
WorkspacePath          := "/home/romanov/work/ccdb/ccdb/projects/CodeLite"
ProjectPath            := "/mnt/work/romanov/ccdb/ccdb/projects/CodeLite"
CurrentFileName        :=
CurrentFilePath        :=
CurrentFileFullPath    :=
User                   :=romanov
Date                   :=01/04/2011
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
OutputFile             :=$(WorkspacePath)/../../web/cgi-bin/ccdb.cgi
Preprocessors          :=
ObjectSwitch           :=-o 
ArchiveOutputSwitch    := 
PreprocessOnlySwitch   :=-E 
MakeDirCommand         :=mkdir -p
CmpOptions             :=$(shell mysql_config --cflags) -g $(Preprocessors)
C_CmpOptions           := -g $(Preprocessors)
LinkOptions            :=  
IncludePath            :=  "$(IncludeSwitch)." "$(IncludeSwitch)$(WorkspacePath)/../../include" "$(IncludeSwitch)." 
RcIncludePath          :=
Libs                   :=$(LibrarySwitch)ccdb 
LibPath                := "$(LibraryPathSwitch)$(shell mysql_config --libs)" "$(LibraryPathSwitch)$(WorkspacePath)/../../lib" 


##
## User defined environment variables
##
CodeLiteDir:=/usr/share/codelite
Objects=$(IntermediateDirectory)/Web_DConfigReader$(ObjectSuffix) $(IntermediateDirectory)/Web_DHttpContext$(ObjectSuffix) $(IntermediateDirectory)/src_mainWeb$(ObjectSuffix) 

##
## Main Build Targets 
##
all: $(OutputFile)

$(OutputFile): makeDirStep $(Objects)
	@$(MakeDirCommand) $(@D)
	$(LinkerName) $(OutputSwitch)$(OutputFile) $(Objects) $(LibPath) $(Libs) $(LinkOptions)

makeDirStep:
	@test -d ./Debug || $(MakeDirCommand) ./Debug

PreBuild:


##
## Objects
##
$(IntermediateDirectory)/Web_DConfigReader$(ObjectSuffix): ../../src/Web/DConfigReader.cc $(IntermediateDirectory)/Web_DConfigReader$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/mnt/work/romanov/ccdb/ccdb/src/Web/DConfigReader.cc" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Web_DConfigReader$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Web_DConfigReader$(DependSuffix): ../../src/Web/DConfigReader.cc
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Web_DConfigReader$(ObjectSuffix) -MF$(IntermediateDirectory)/Web_DConfigReader$(DependSuffix) -MM "/mnt/work/romanov/ccdb/ccdb/src/Web/DConfigReader.cc"

$(IntermediateDirectory)/Web_DConfigReader$(PreprocessSuffix): ../../src/Web/DConfigReader.cc
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Web_DConfigReader$(PreprocessSuffix) "/mnt/work/romanov/ccdb/ccdb/src/Web/DConfigReader.cc"

$(IntermediateDirectory)/Web_DHttpContext$(ObjectSuffix): ../../src/Web/DHttpContext.cc $(IntermediateDirectory)/Web_DHttpContext$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/mnt/work/romanov/ccdb/ccdb/src/Web/DHttpContext.cc" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Web_DHttpContext$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Web_DHttpContext$(DependSuffix): ../../src/Web/DHttpContext.cc
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Web_DHttpContext$(ObjectSuffix) -MF$(IntermediateDirectory)/Web_DHttpContext$(DependSuffix) -MM "/mnt/work/romanov/ccdb/ccdb/src/Web/DHttpContext.cc"

$(IntermediateDirectory)/Web_DHttpContext$(PreprocessSuffix): ../../src/Web/DHttpContext.cc
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Web_DHttpContext$(PreprocessSuffix) "/mnt/work/romanov/ccdb/ccdb/src/Web/DHttpContext.cc"

$(IntermediateDirectory)/src_mainWeb$(ObjectSuffix): ../../src/mainWeb.cc $(IntermediateDirectory)/src_mainWeb$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/mnt/work/romanov/ccdb/ccdb/src/mainWeb.cc" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/src_mainWeb$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/src_mainWeb$(DependSuffix): ../../src/mainWeb.cc
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/src_mainWeb$(ObjectSuffix) -MF$(IntermediateDirectory)/src_mainWeb$(DependSuffix) -MM "/mnt/work/romanov/ccdb/ccdb/src/mainWeb.cc"

$(IntermediateDirectory)/src_mainWeb$(PreprocessSuffix): ../../src/mainWeb.cc
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/src_mainWeb$(PreprocessSuffix) "/mnt/work/romanov/ccdb/ccdb/src/mainWeb.cc"


-include $(IntermediateDirectory)/*$(DependSuffix)
##
## Clean
##
clean:
	$(RM) $(IntermediateDirectory)/Web_DConfigReader$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Web_DConfigReader$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Web_DConfigReader$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Web_DHttpContext$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Web_DHttpContext$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Web_DHttpContext$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/src_mainWeb$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/src_mainWeb$(DependSuffix)
	$(RM) $(IntermediateDirectory)/src_mainWeb$(PreprocessSuffix)
	$(RM) $(OutputFile)


