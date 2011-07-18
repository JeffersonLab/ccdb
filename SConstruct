import sys
import os

#Setup default environment. This environment 

#add some colors 
colors = {
	'cyan':'\033[96m', 
	'purple':'\033[95m', 
	'blue':'\033[94m', 
	'green':'\033[92m', 
	'yellow':'\033[93m',
	'red':'\033[91m', 
	'end':'\033[0m'}
 
#If the output is not a terminal, remove the colors
if not sys.stdout.isatty():
    for key, value in colors.iteritems():
        colors[key] = ''
 
compile_source_message        = '%sCompiling %s==> %s$SOURCE%s' % (colors['blue'], colors['purple'], colors['yellow'], colors['end'])
compile_shared_source_message = '%sCompiling shared %s==> %s$SOURCE%s' % (colors['blue'], colors['purple'], colors['yellow'], colors['end'])
link_program_message          = '%sLinking Program %s==> %s$TARGET%s' % (colors['red'], colors['purple'], colors['yellow'], colors['end'])
link_library_message          = '%sLinking Static Library %s==> %s$TARGET%s' % (colors['red'], colors['purple'], colors['yellow'], colors['end'])
ranlib_library_message        = '%sRanlib Library %s==> %s$TARGET%s' % (colors['red'], colors['purple'], colors['yellow'], colors['end'])
link_shared_library_message   = '%sLinking Shared Library %s==> %s$TARGET%s' % (colors['red'], colors['purple'], colors['yellow'], colors['end'])
java_library_message          = '%sCreating Java Archive %s==> %s$TARGET%s' % (colors['red'], colors['purple'], colors['yellow'], colors['end'])

#Create 'default' environment. Other environments will be a copy of this one
default_env = Environment(
    #Messages
    CXXCOMSTR = compile_source_message, 
    CCCOMSTR = compile_source_message,
    SHCCCOMSTR = compile_shared_source_message,
    SHCXXCOMSTR = compile_shared_source_message,
    ARCOMSTR = link_library_message,
    RANLIBCOMSTR = ranlib_library_message,
    SHLINKCOMSTR = link_shared_library_message,
    LINKCOMSTR = link_program_message,
    JARCOMSTR = java_library_message,
    JAVACCOMSTR = compile_source_message,
    
    #>> CCDB related default staff <<
    CPPPATH = ['#include', 'src'],
    ENV = os.environ,
)

#Export 'default' environment for everything that whishes to use it
Export('default_env') 

#Create 'working' environment
env = default_env.Clone()
env.Repository('src')

#Attach SConsctipts
SConscript('src/SConscript', 'env', variant_dir='tmp', duplicate=0)
SConscript('swig/SConscript', 'env', variant_dir='tmp/swig', duplicate=0)

