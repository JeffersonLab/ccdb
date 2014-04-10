#
# Generated Makefile - do not edit!
#
# Edit the Makefile in the project folder instead (../Makefile). Each target
# has a -pre and a -post target defined where you can add customized code.
#
# This makefile implements configuration specific macros and targets.


# Environment
MKDIR=mkdir
CP=cp
GREP=grep
NM=nm
CCADMIN=CCadmin
RANLIB=ranlib
CC=clang
CCC=clang++
CXX=clang++
FC=gfortran
AS=as

# Macros
CND_PLATFORM=CLang-Linux-x86
CND_DLIB_EXT=so
CND_CONF=Release
CND_DISTDIR=dist
CND_BUILDDIR=build

# Include project Makefile
include Makefile

# Object Directory
OBJECTDIR=${CND_BUILDDIR}/${CND_CONF}/${CND_PLATFORM}

# Object Files
OBJECTFILES= \
	${OBJECTDIR}/_ext/1001602298/test_Authentication.o \
	${OBJECTDIR}/_ext/1001602298/test_Console.o \
	${OBJECTDIR}/_ext/1001602298/test_ModelObjects.o \
	${OBJECTDIR}/_ext/1001602298/test_MySQLProvider.o \
	${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Assignments.o \
	${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Connection.o \
	${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Directories.o \
	${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Other.o \
	${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_RunRanges.o \
	${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_TypeTables.o \
	${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Variations.o \
	${OBJECTDIR}/_ext/1001602298/test_MySqlUserAPI.o \
	${OBJECTDIR}/_ext/1001602298/test_NoMySqlUserAPI.o \
	${OBJECTDIR}/_ext/1001602298/test_PathUtils.o \
	${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider.o \
	${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Assignments.o \
	${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Connection.o \
	${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Directories.o \
	${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Other.o \
	${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_RunRanges.o \
	${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_TypeTables.o \
	${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Variations.o \
	${OBJECTDIR}/_ext/1001602298/test_StringUtils.o \
	${OBJECTDIR}/_ext/1001602298/test_TimeProvider.o \
	${OBJECTDIR}/_ext/1001602298/tests.o


# C Compiler Flags
CFLAGS=

# CC Compiler Flags
CCFLAGS=
CXXFLAGS=

# Fortran Compiler Flags
FFLAGS=

# Assembler Flags
ASFLAGS=

# Link Libraries and Options
LDLIBSOPTIONS=

# Build Targets
.build-conf: ${BUILD_SUBPROJECTS}
	"${MAKE}"  -f nbproject/Makefile-${CND_CONF}.mk ${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}/tests

${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}/tests: ${OBJECTFILES}
	${MKDIR} -p ${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}
	${LINK.cc} -o ${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}/tests ${OBJECTFILES} ${LDLIBSOPTIONS}

${OBJECTDIR}/_ext/1001602298/test_Authentication.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_Authentication.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_Authentication.o /home/romanov/halld/ccdb/trunk/src/Tests/test_Authentication.cc

${OBJECTDIR}/_ext/1001602298/test_Console.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_Console.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_Console.o /home/romanov/halld/ccdb/trunk/src/Tests/test_Console.cc

${OBJECTDIR}/_ext/1001602298/test_ModelObjects.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_ModelObjects.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_ModelObjects.o /home/romanov/halld/ccdb/trunk/src/Tests/test_ModelObjects.cc

${OBJECTDIR}/_ext/1001602298/test_MySQLProvider.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_MySQLProvider.o /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider.cc

${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Assignments.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_Assignments.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Assignments.o /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_Assignments.cc

${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Connection.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_Connection.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Connection.o /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_Connection.cc

${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Directories.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_Directories.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Directories.o /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_Directories.cc

${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Other.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_Other.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Other.o /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_Other.cc

${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_RunRanges.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_RunRanges.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_RunRanges.o /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_RunRanges.cc

${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_TypeTables.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_TypeTables.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_TypeTables.o /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_TypeTables.cc

${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Variations.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_Variations.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_MySQLProvider_Variations.o /home/romanov/halld/ccdb/trunk/src/Tests/test_MySQLProvider_Variations.cc

${OBJECTDIR}/_ext/1001602298/test_MySqlUserAPI.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_MySqlUserAPI.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_MySqlUserAPI.o /home/romanov/halld/ccdb/trunk/src/Tests/test_MySqlUserAPI.cc

${OBJECTDIR}/_ext/1001602298/test_NoMySqlUserAPI.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_NoMySqlUserAPI.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_NoMySqlUserAPI.o /home/romanov/halld/ccdb/trunk/src/Tests/test_NoMySqlUserAPI.cc

${OBJECTDIR}/_ext/1001602298/test_PathUtils.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_PathUtils.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_PathUtils.o /home/romanov/halld/ccdb/trunk/src/Tests/test_PathUtils.cc

${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider.o /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider.cc

${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Assignments.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_Assignments.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Assignments.o /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_Assignments.cc

${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Connection.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_Connection.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Connection.o /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_Connection.cc

${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Directories.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_Directories.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Directories.o /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_Directories.cc

${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Other.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_Other.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Other.o /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_Other.cc

${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_RunRanges.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_RunRanges.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_RunRanges.o /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_RunRanges.cc

${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_TypeTables.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_TypeTables.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_TypeTables.o /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_TypeTables.cc

${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Variations.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_Variations.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_SQLiteProvider_Variations.o /home/romanov/halld/ccdb/trunk/src/Tests/test_SQLiteProvider_Variations.cc

${OBJECTDIR}/_ext/1001602298/test_StringUtils.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_StringUtils.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_StringUtils.o /home/romanov/halld/ccdb/trunk/src/Tests/test_StringUtils.cc

${OBJECTDIR}/_ext/1001602298/test_TimeProvider.o: /home/romanov/halld/ccdb/trunk/src/Tests/test_TimeProvider.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/test_TimeProvider.o /home/romanov/halld/ccdb/trunk/src/Tests/test_TimeProvider.cc

${OBJECTDIR}/_ext/1001602298/tests.o: /home/romanov/halld/ccdb/trunk/src/Tests/tests.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1001602298
	${RM} "$@.d"
	$(COMPILE.cc) -O2 -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1001602298/tests.o /home/romanov/halld/ccdb/trunk/src/Tests/tests.cc

# Subprojects
.build-subprojects:

# Clean Targets
.clean-conf: ${CLEAN_SUBPROJECTS}
	${RM} -r ${CND_BUILDDIR}/${CND_CONF}
	${RM} ${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}/tests

# Subprojects
.clean-subprojects:

# Enable dependency checking
.dep.inc: .depcheck-impl

include .dep.inc
