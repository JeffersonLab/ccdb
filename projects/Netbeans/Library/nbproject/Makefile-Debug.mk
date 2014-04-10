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
CND_CONF=Debug
CND_DISTDIR=dist
CND_BUILDDIR=build

# Include project Makefile
include Makefile

# Object Directory
OBJECTDIR=${CND_BUILDDIR}/${CND_CONF}/${CND_PLATFORM}

# Object Files
OBJECTFILES= \
	${OBJECTDIR}/_ext/1931398335/CCDBError.o \
	${OBJECTDIR}/_ext/1931398335/Calibration.o \
	${OBJECTDIR}/_ext/1931398335/CalibrationGenerator.o \
	${OBJECTDIR}/_ext/1931398335/Console.o \
	${OBJECTDIR}/_ext/1931398335/GlobalMutex.o \
	${OBJECTDIR}/_ext/150347159/PathUtils.o \
	${OBJECTDIR}/_ext/150347159/Stopwatch.o \
	${OBJECTDIR}/_ext/150347159/StringUtils.o \
	${OBJECTDIR}/_ext/150347159/TimeProvider.o \
	${OBJECTDIR}/_ext/150347159/WorkUtils.o \
	${OBJECTDIR}/_ext/1931398335/IMutex.o \
	${OBJECTDIR}/_ext/1931398335/ISyncObject.o \
	${OBJECTDIR}/_ext/1931398335/Log.o \
	${OBJECTDIR}/_ext/1091096251/Assignment.o \
	${OBJECTDIR}/_ext/1091096251/ConstantsTypeColumn.o \
	${OBJECTDIR}/_ext/1091096251/ConstantsTypeTable.o \
	${OBJECTDIR}/_ext/1091096251/Directory.o \
	${OBJECTDIR}/_ext/1091096251/EventRange.o \
	${OBJECTDIR}/_ext/1091096251/ObjectsOwner.o \
	${OBJECTDIR}/_ext/1091096251/RunRange.o \
	${OBJECTDIR}/_ext/1091096251/StoredObject.o \
	${OBJECTDIR}/_ext/1091096251/Variation.o \
	${OBJECTDIR}/_ext/1931398335/MySQLCalibration.o \
	${OBJECTDIR}/_ext/899248948/DataProvider.o \
	${OBJECTDIR}/_ext/899248948/EnvironmentAuthentication.o \
	${OBJECTDIR}/_ext/899248948/FileDataProvider.o \
	${OBJECTDIR}/_ext/899248948/IAuthentication.o \
	${OBJECTDIR}/_ext/899248948/MySQLConnectionInfo.o \
	${OBJECTDIR}/_ext/899248948/MySQLDataProvider.o \
	${OBJECTDIR}/_ext/899248948/SQLiteDataProvider.o \
	${OBJECTDIR}/_ext/1931398335/PthreadMutex.o \
	${OBJECTDIR}/_ext/1931398335/PthreadSyncObject.o \
	${OBJECTDIR}/_ext/1931398335/SQLiteCalibration.o \
	${OBJECTDIR}/_ext/936628307/sqlite3.o


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
LDLIBSOPTIONS=-lpthread /usr/lib/x86_64-linux-gnu/libmysqlclient.so

# Build Targets
.build-conf: ${BUILD_SUBPROJECTS}
	"${MAKE}"  -f nbproject/Makefile-${CND_CONF}.mk ${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}/libLibrary.${CND_DLIB_EXT}

${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}/libLibrary.${CND_DLIB_EXT}: /usr/lib/x86_64-linux-gnu/libmysqlclient.so

${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}/libLibrary.${CND_DLIB_EXT}: ${OBJECTFILES}
	${MKDIR} -p ${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}
	${LINK.cc} -o ${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}/libLibrary.${CND_DLIB_EXT} ${OBJECTFILES} ${LDLIBSOPTIONS} -shared -fPIC

${OBJECTDIR}/_ext/1931398335/CCDBError.o: ../../../src/Library/CCDBError.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/CCDBError.o ../../../src/Library/CCDBError.cc

${OBJECTDIR}/_ext/1931398335/Calibration.o: ../../../src/Library/Calibration.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/Calibration.o ../../../src/Library/Calibration.cc

${OBJECTDIR}/_ext/1931398335/CalibrationGenerator.o: ../../../src/Library/CalibrationGenerator.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/CalibrationGenerator.o ../../../src/Library/CalibrationGenerator.cc

${OBJECTDIR}/_ext/1931398335/Console.o: ../../../src/Library/Console.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/Console.o ../../../src/Library/Console.cc

${OBJECTDIR}/_ext/1931398335/GlobalMutex.o: ../../../src/Library/GlobalMutex.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/GlobalMutex.o ../../../src/Library/GlobalMutex.cc

${OBJECTDIR}/_ext/150347159/PathUtils.o: ../../../src/Library/Helpers/PathUtils.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/150347159
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/150347159/PathUtils.o ../../../src/Library/Helpers/PathUtils.cc

${OBJECTDIR}/_ext/150347159/Stopwatch.o: ../../../src/Library/Helpers/Stopwatch.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/150347159
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/150347159/Stopwatch.o ../../../src/Library/Helpers/Stopwatch.cc

${OBJECTDIR}/_ext/150347159/StringUtils.o: ../../../src/Library/Helpers/StringUtils.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/150347159
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/150347159/StringUtils.o ../../../src/Library/Helpers/StringUtils.cc

${OBJECTDIR}/_ext/150347159/TimeProvider.o: ../../../src/Library/Helpers/TimeProvider.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/150347159
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/150347159/TimeProvider.o ../../../src/Library/Helpers/TimeProvider.cc

${OBJECTDIR}/_ext/150347159/WorkUtils.o: ../../../src/Library/Helpers/WorkUtils.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/150347159
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/150347159/WorkUtils.o ../../../src/Library/Helpers/WorkUtils.cc

${OBJECTDIR}/_ext/1931398335/IMutex.o: ../../../src/Library/IMutex.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/IMutex.o ../../../src/Library/IMutex.cc

${OBJECTDIR}/_ext/1931398335/ISyncObject.o: ../../../src/Library/ISyncObject.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/ISyncObject.o ../../../src/Library/ISyncObject.cc

${OBJECTDIR}/_ext/1931398335/Log.o: ../../../src/Library/Log.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/Log.o ../../../src/Library/Log.cc

${OBJECTDIR}/_ext/1091096251/Assignment.o: ../../../src/Library/Model/Assignment.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1091096251
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1091096251/Assignment.o ../../../src/Library/Model/Assignment.cc

${OBJECTDIR}/_ext/1091096251/ConstantsTypeColumn.o: ../../../src/Library/Model/ConstantsTypeColumn.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1091096251
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1091096251/ConstantsTypeColumn.o ../../../src/Library/Model/ConstantsTypeColumn.cc

${OBJECTDIR}/_ext/1091096251/ConstantsTypeTable.o: ../../../src/Library/Model/ConstantsTypeTable.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1091096251
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1091096251/ConstantsTypeTable.o ../../../src/Library/Model/ConstantsTypeTable.cc

${OBJECTDIR}/_ext/1091096251/Directory.o: ../../../src/Library/Model/Directory.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1091096251
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1091096251/Directory.o ../../../src/Library/Model/Directory.cc

${OBJECTDIR}/_ext/1091096251/EventRange.o: ../../../src/Library/Model/EventRange.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1091096251
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1091096251/EventRange.o ../../../src/Library/Model/EventRange.cc

${OBJECTDIR}/_ext/1091096251/ObjectsOwner.o: ../../../src/Library/Model/ObjectsOwner.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1091096251
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1091096251/ObjectsOwner.o ../../../src/Library/Model/ObjectsOwner.cc

${OBJECTDIR}/_ext/1091096251/RunRange.o: ../../../src/Library/Model/RunRange.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1091096251
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1091096251/RunRange.o ../../../src/Library/Model/RunRange.cc

${OBJECTDIR}/_ext/1091096251/StoredObject.o: ../../../src/Library/Model/StoredObject.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1091096251
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1091096251/StoredObject.o ../../../src/Library/Model/StoredObject.cc

${OBJECTDIR}/_ext/1091096251/Variation.o: ../../../src/Library/Model/Variation.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1091096251
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1091096251/Variation.o ../../../src/Library/Model/Variation.cc

${OBJECTDIR}/_ext/1931398335/MySQLCalibration.o: ../../../src/Library/MySQLCalibration.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/MySQLCalibration.o ../../../src/Library/MySQLCalibration.cc

${OBJECTDIR}/_ext/899248948/DataProvider.o: ../../../src/Library/Providers/DataProvider.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/899248948
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/899248948/DataProvider.o ../../../src/Library/Providers/DataProvider.cc

${OBJECTDIR}/_ext/899248948/EnvironmentAuthentication.o: ../../../src/Library/Providers/EnvironmentAuthentication.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/899248948
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/899248948/EnvironmentAuthentication.o ../../../src/Library/Providers/EnvironmentAuthentication.cc

${OBJECTDIR}/_ext/899248948/FileDataProvider.o: ../../../src/Library/Providers/FileDataProvider.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/899248948
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/899248948/FileDataProvider.o ../../../src/Library/Providers/FileDataProvider.cc

${OBJECTDIR}/_ext/899248948/IAuthentication.o: ../../../src/Library/Providers/IAuthentication.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/899248948
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/899248948/IAuthentication.o ../../../src/Library/Providers/IAuthentication.cc

${OBJECTDIR}/_ext/899248948/MySQLConnectionInfo.o: ../../../src/Library/Providers/MySQLConnectionInfo.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/899248948
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/899248948/MySQLConnectionInfo.o ../../../src/Library/Providers/MySQLConnectionInfo.cc

${OBJECTDIR}/_ext/899248948/MySQLDataProvider.o: ../../../src/Library/Providers/MySQLDataProvider.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/899248948
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/899248948/MySQLDataProvider.o ../../../src/Library/Providers/MySQLDataProvider.cc

${OBJECTDIR}/_ext/899248948/SQLiteDataProvider.o: ../../../src/Library/Providers/SQLiteDataProvider.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/899248948
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/899248948/SQLiteDataProvider.o ../../../src/Library/Providers/SQLiteDataProvider.cc

${OBJECTDIR}/_ext/1931398335/PthreadMutex.o: ../../../src/Library/PthreadMutex.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/PthreadMutex.o ../../../src/Library/PthreadMutex.cc

${OBJECTDIR}/_ext/1931398335/PthreadSyncObject.o: ../../../src/Library/PthreadSyncObject.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/PthreadSyncObject.o ../../../src/Library/PthreadSyncObject.cc

${OBJECTDIR}/_ext/1931398335/SQLiteCalibration.o: ../../../src/Library/SQLiteCalibration.cc 
	${MKDIR} -p ${OBJECTDIR}/_ext/1931398335
	${RM} "$@.d"
	$(COMPILE.cc) -g -DCCDB_MYSQL -I../../../include -I../../../include/SQLite -I/usr/include/mysql -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/1931398335/SQLiteCalibration.o ../../../src/Library/SQLiteCalibration.cc

${OBJECTDIR}/_ext/936628307/sqlite3.o: /home/romanov/halld/ccdb/trunk/src/SQLite/sqlite3.c 
	${MKDIR} -p ${OBJECTDIR}/_ext/936628307
	${RM} "$@.d"
	$(COMPILE.c) -g -fPIC  -MMD -MP -MF "$@.d" -o ${OBJECTDIR}/_ext/936628307/sqlite3.o /home/romanov/halld/ccdb/trunk/src/SQLite/sqlite3.c

# Subprojects
.build-subprojects:

# Clean Targets
.clean-conf: ${CLEAN_SUBPROJECTS}
	${RM} -r ${CND_BUILDDIR}/${CND_CONF}
	${RM} ${CND_DISTDIR}/${CND_CONF}/${CND_PLATFORM}/libLibrary.${CND_DLIB_EXT}

# Subprojects
.clean-subprojects:

# Enable dependency checking
.dep.inc: .depcheck-impl

include .dep.inc
