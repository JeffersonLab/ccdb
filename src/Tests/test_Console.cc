#include "CCDB/Console.h"
#include "CCDB/Helpers/StringUtils.h"

using namespace std;
using namespace ccdb;

TEST_CASE("CCDB/Console","")
{
	Console console;
	console.SetUseColors(true);

	
	//Wite line test
	console.WriteLine("test console.WriteLine %i \n",6);
	
	//write test
	console.Write("test %i |",6);
	console.Write(" Write |");
	console.WriteLine(" and WriteLine |");

	//Test of SetTextParams - setting different colors and cases
	console.SetTextParams(Console::cBright, Console::cRed, Console::cBlack);
	console.WriteLine("test console.SetTextParams(cBright, cRed, cBlack)");

	console.SetTextParams(Console::cReset, Console::cRed, Console::cBlack);
	console.WriteLine(Console::cRed,"test colors console.SetTextParams(Console::cReset, Console::cRed, Console::cBlack);");

	console.SetTextParams(0, Console::cBrightGreen, Console::cBlue);
	console.WriteLine(Console::cRed,"test colors console.SetTextParams(0, Console::cBrightGreen, Console::cBlue);");	

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
	console.Write(Console::cBrightCyan," more cyan %f ", 22.2);
	console.Write("uuu ");
	console.WriteLine(Console::cBrightYellow,"test console.Write(Console::cBrightYellow... !");

	//Finally we return the original colors
	console.ResetTextProperties();

	return true;
}