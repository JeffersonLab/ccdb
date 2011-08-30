// $Id$
//
//    File: DEventProcessor_a.cc
// Created: Mon Aug 29 13:19:28 EDT 2011
// Creator: romanov (on Linux localhost.localdomain 2.6.40.3-0.fc15.x86_64 x86_64)
//

#include <iostream>

using namespace std;
using namespace jana;


// Routine used to create our DEventProcessor
#include <JANA/JApplication.h>
#include <JCalibrationGeneratorCCDB.h>
extern "C"{
void InitPlugin(JApplication *app){
	InitJANAPlugin(app);
    app->AddCalibrationGenerator(new JCalibrationWSGenerator());
    cout <<"jana_ccdb gained control and now do whatever it wants"<<endl;
}
} 
