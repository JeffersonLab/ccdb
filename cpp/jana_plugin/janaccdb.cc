// $Id$
//
//    File: DEventProcessor_a.cc
// Created: Mon Aug 29 13:19:28 EDT 2011
// Creator: romanov (on Linux localhost.localdomain 2.6.40.3-0.fc15.x86_64 x86_64)
//

#include <iostream>

// Routine used to create our DEventProcessor
#include <JANA/JApplication.h>
#include <JCalibrationGeneratorCCDB.h>

using namespace std;
using namespace jana;


extern "C"
{
	void InitPlugin(jana::JApplication *app)
	{
		InitJANAPlugin(app);

		#ifdef CCDB_DEBUG_OUTPUT
		cout <<"CCDB::janaccdb gained control and now do whatever it wants"<<endl;
		#endif

		app->AddCalibrationGenerator(new JCalibrationGeneratorCCDB());

		#ifdef CCDB_DEBUG_OUTPUT
		cout <<"CCDB::janaccdb just did app->AddCalibrationGenerator(new JCalibrationGeneratorCCDB())"<<endl;
		#endif
	}
} 
