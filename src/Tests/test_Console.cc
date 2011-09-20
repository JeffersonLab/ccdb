#include "DConsole.h"
#include "DStringUtils.h"

using namespace std;
using namespace ccdb;

bool test_DConsole()
{
	DConsole console;
	console.SetUseColors(true);

	//Formatting tests
	cout<<DStringUtils::Format("test console.Format %i %f", 5, 3.14)<<endl;
	cout<<DStringUtils::Format("test long string console.Format aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa %i %f", 5, 3.14)<<endl;

	//Wite line test
	console.WriteLine("test console.WriteLine %i \n",6);
	
	//write test
	console.Write("test %i |",6);
	console.Write(" Write |");
	console.WriteLine(" and WriteLine |");

	//Test of SetTextParams - setting different colors and cases
	console.SetTextParams(DConsole::cBright, DConsole::cRed, DConsole::cBlack);
	console.WriteLine("test console.SetTextParams(cBright, cRed, cBlack)");

	console.SetTextParams(DConsole::cReset, DConsole::cRed, DConsole::cBlack);
	console.WriteLine(DConsole::cRed,"test colors console.SetTextParams(DConsole::cReset, DConsole::cRed, DConsole::cBlack);");

	console.SetTextParams(0, DConsole::cBrightGreen, DConsole::cBlue);
	console.WriteLine(DConsole::cRed,"test colors console.SetTextParams(0, DConsole::cBrightGreen, DConsole::cBlue);");

	//test of resetting the params
	console.ResetTextProperties();
	console.WriteLine("test console.ResetTextProperties();");

	//write line with no arguments must place new line
	console.WriteLine();
	console.WriteLine("test console.WriteLine();");
	console.WriteLine("test console.WriteLine()2;");
	
	//Testing write
	//cout<<"joke";
	console.Write("test console.Write | ");
	console.Write(DConsole::cBrightCyan," more cyan %f ", 22.2);
	console.Write("uuu ");
	console.WriteLine(DConsole::cBrightYellow,"test console.Write(DConsole::cBrightYellow... !");

	//Finally we return the original colors
	console.ResetTextProperties();

	return true;
}