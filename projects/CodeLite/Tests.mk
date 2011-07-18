##
## Auto Generated makefile by CodeLite IDE
## any manual changes will be erased      
##
## Debug
ProjectName            :=Tests
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
OutputFile             :=$(WorkspacePath)/../../bin/tests
Preprocessors          :=
ObjectSwitch           :=-o 
ArchiveOutputSwitch    := 
PreprocessOnlySwitch   :=-E 
ObjectsFileList        :="/media/sf_ccdb/projects/CodeLite/Tests.txt"
MakeDirCommand         :=mkdir -p
CmpOptions             :=$(shell mysql_config --cflags) -g $(Preprocessors)
C_CmpOptions           := -g $(Preprocessors)
LinkOptions            :=  
IncludePath            :=  $(IncludeSwitch). $(IncludeSwitch)$(WorkspacePath)/../../include $(IncludeSwitch). 
RcIncludePath          :=
Libs                   :=$(LibrarySwitch)ccdb 
LibPath                := $(LibraryPathSwitch)"$(shell mysql_config --libs)" $(LibraryPathSwitch)$(WorkspacePath)/../../lib 


##
## User defined environment variables
##
CodeLiteDir:=/usr/share/codelite
Objects=$(IntermediateDirectory)/Tests_benchmark_Providers$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_DConsole$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_DMySQLProvider$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(ObjectSuffix) \
	$(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_DStringUtils$(ObjectSuffix) $(IntermediateDirectory)/Tests_test_ModelObjects$(ObjectSuffix) $(IntermediateDirectory)/src_mainTests$(ObjectSuffix) $(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(ObjectSuffix) 

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
$(IntermediateDirectory)/Tests_benchmark_Providers$(ObjectSuffix): ../../src/Tests/benchmark_Providers.cpp $(IntermediateDirectory)/Tests_benchmark_Providers$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/benchmark_Providers.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_benchmark_Providers$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_benchmark_Providers$(DependSuffix): ../../src/Tests/benchmark_Providers.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_benchmark_Providers$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_benchmark_Providers$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/benchmark_Providers.cpp"

$(IntermediateDirectory)/Tests_benchmark_Providers$(PreprocessSuffix): ../../src/Tests/benchmark_Providers.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_benchmark_Providers$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/benchmark_Providers.cpp"

$(IntermediateDirectory)/Tests_test_DConsole$(ObjectSuffix): ../../src/Tests/test_DConsole.cpp $(IntermediateDirectory)/Tests_test_DConsole$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DConsole.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DConsole$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DConsole$(DependSuffix): ../../src/Tests/test_DConsole.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DConsole$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DConsole$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DConsole.cpp"

$(IntermediateDirectory)/Tests_test_DConsole$(PreprocessSuffix): ../../src/Tests/test_DConsole.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DConsole$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DConsole.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider$(ObjectSuffix): ../../src/Tests/test_DMySQLProvider.cpp $(IntermediateDirectory)/Tests_test_DMySQLProvider$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DMySQLProvider.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DMySQLProvider$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DMySQLProvider$(DependSuffix): ../../src/Tests/test_DMySQLProvider.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DMySQLProvider$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DMySQLProvider$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DMySQLProvider.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider$(PreprocessSuffix): ../../src/Tests/test_DMySQLProvider.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DMySQLProvider$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DMySQLProvider.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(ObjectSuffix): ../../src/Tests/test_DMySQLProvider_Assignments.cpp $(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Assignments.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(DependSuffix): ../../src/Tests/test_DMySQLProvider_Assignments.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Assignments.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(PreprocessSuffix): ../../src/Tests/test_DMySQLProvider_Assignments.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Assignments.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(ObjectSuffix): ../../src/Tests/test_DMySQLProvider_Connection.cpp $(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Connection.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(DependSuffix): ../../src/Tests/test_DMySQLProvider_Connection.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Connection.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(PreprocessSuffix): ../../src/Tests/test_DMySQLProvider_Connection.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Connection.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(ObjectSuffix): ../../src/Tests/test_DMySQLProvider_Directories.cpp $(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Directories.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(DependSuffix): ../../src/Tests/test_DMySQLProvider_Directories.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Directories.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(PreprocessSuffix): ../../src/Tests/test_DMySQLProvider_Directories.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Directories.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(ObjectSuffix): ../../src/Tests/test_DMySQLProvider_Other.cpp $(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Other.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(DependSuffix): ../../src/Tests/test_DMySQLProvider_Other.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Other.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(PreprocessSuffix): ../../src/Tests/test_DMySQLProvider_Other.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Other.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(ObjectSuffix): ../../src/Tests/test_DMySQLProvider_RunRanges.cpp $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_RunRanges.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(DependSuffix): ../../src/Tests/test_DMySQLProvider_RunRanges.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DMySQLProvider_RunRanges.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(PreprocessSuffix): ../../src/Tests/test_DMySQLProvider_RunRanges.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_RunRanges.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(ObjectSuffix): ../../src/Tests/test_DMySQLProvider_RunRangesVariations.cpp $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_RunRangesVariations.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(DependSuffix): ../../src/Tests/test_DMySQLProvider_RunRangesVariations.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DMySQLProvider_RunRangesVariations.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(PreprocessSuffix): ../../src/Tests/test_DMySQLProvider_RunRangesVariations.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_RunRangesVariations.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(ObjectSuffix): ../../src/Tests/test_DMySQLProvider_TypeTables.cpp $(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_TypeTables.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(DependSuffix): ../../src/Tests/test_DMySQLProvider_TypeTables.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DMySQLProvider_TypeTables.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(PreprocessSuffix): ../../src/Tests/test_DMySQLProvider_TypeTables.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_TypeTables.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(ObjectSuffix): ../../src/Tests/test_DMySQLProvider_Variations.cpp $(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Variations.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(DependSuffix): ../../src/Tests/test_DMySQLProvider_Variations.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Variations.cpp"

$(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(PreprocessSuffix): ../../src/Tests/test_DMySQLProvider_Variations.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DMySQLProvider_Variations.cpp"

$(IntermediateDirectory)/Tests_test_DStringUtils$(ObjectSuffix): ../../src/Tests/test_DStringUtils.cpp $(IntermediateDirectory)/Tests_test_DStringUtils$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_DStringUtils.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_DStringUtils$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_DStringUtils$(DependSuffix): ../../src/Tests/test_DStringUtils.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_DStringUtils$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_DStringUtils$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_DStringUtils.cpp"

$(IntermediateDirectory)/Tests_test_DStringUtils$(PreprocessSuffix): ../../src/Tests/test_DStringUtils.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_DStringUtils$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_DStringUtils.cpp"

$(IntermediateDirectory)/Tests_test_ModelObjects$(ObjectSuffix): ../../src/Tests/test_ModelObjects.cpp $(IntermediateDirectory)/Tests_test_ModelObjects$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/test_ModelObjects.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_test_ModelObjects$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_test_ModelObjects$(DependSuffix): ../../src/Tests/test_ModelObjects.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_test_ModelObjects$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_test_ModelObjects$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/test_ModelObjects.cpp"

$(IntermediateDirectory)/Tests_test_ModelObjects$(PreprocessSuffix): ../../src/Tests/test_ModelObjects.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_test_ModelObjects$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/test_ModelObjects.cpp"

$(IntermediateDirectory)/src_mainTests$(ObjectSuffix): ../../src/mainTests.cc $(IntermediateDirectory)/src_mainTests$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/mainTests.cc" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/src_mainTests$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/src_mainTests$(DependSuffix): ../../src/mainTests.cc
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/src_mainTests$(ObjectSuffix) -MF$(IntermediateDirectory)/src_mainTests$(DependSuffix) -MM "/media/sf_ccdb/src/mainTests.cc"

$(IntermediateDirectory)/src_mainTests$(PreprocessSuffix): ../../src/mainTests.cc
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/src_mainTests$(PreprocessSuffix) "/media/sf_ccdb/src/mainTests.cc"

$(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(ObjectSuffix): ../../src/Tests/benchmark_PreparedStatements.cpp $(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(DependSuffix)
	$(CompilerName) $(SourceSwitch) "/media/sf_ccdb/src/Tests/benchmark_PreparedStatements.cpp" $(CmpOptions) $(ObjectSwitch)$(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(ObjectSuffix) $(IncludePath)
$(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(DependSuffix): ../../src/Tests/benchmark_PreparedStatements.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) -MG -MP -MT$(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(ObjectSuffix) -MF$(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(DependSuffix) -MM "/media/sf_ccdb/src/Tests/benchmark_PreparedStatements.cpp"

$(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(PreprocessSuffix): ../../src/Tests/benchmark_PreparedStatements.cpp
	@$(CompilerName) $(CmpOptions) $(IncludePath) $(PreprocessOnlySwitch) $(OutputSwitch) $(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(PreprocessSuffix) "/media/sf_ccdb/src/Tests/benchmark_PreparedStatements.cpp"


-include $(IntermediateDirectory)/*$(DependSuffix)
##
## Clean
##
clean:
	$(RM) $(IntermediateDirectory)/Tests_benchmark_Providers$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_benchmark_Providers$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_benchmark_Providers$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DConsole$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DConsole$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DConsole$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Assignments$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Connection$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Directories$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Other$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRanges$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_RunRangesVariations$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_TypeTables$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DMySQLProvider_Variations$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DStringUtils$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DStringUtils$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_DStringUtils$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_ModelObjects$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_ModelObjects$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_test_ModelObjects$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/src_mainTests$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/src_mainTests$(DependSuffix)
	$(RM) $(IntermediateDirectory)/src_mainTests$(PreprocessSuffix)
	$(RM) $(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(ObjectSuffix)
	$(RM) $(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(DependSuffix)
	$(RM) $(IntermediateDirectory)/Tests_benchmark_PreparedStatements$(PreprocessSuffix)
	$(RM) $(OutputFile)


