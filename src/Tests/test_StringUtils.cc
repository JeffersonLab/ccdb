#ifndef test_StringUtils_h
#define test_StringUtils_h

#include "CCDB/Helpers/StringUtils.h"
#include <vector>
#include <string>
#include "Tests/tests_macros.h"

using namespace std;
using namespace ccdb;

bool test_StringUtils()
{
	TESTS_INIT(" - - - StringUtils tests - - - ")
	
	//simple tokenize
	vector<string> tokens = StringUtils::SplitStringToData( " 123 123.12	555 #jhon 987");
	cout<<endl<<"tokenize:"<<endl<<"'123 123	555 #jhon 987'"<<endl<<"tokens:"<<endl;
	for(size_t i=0; i<tokens.size(); i++)
	{
		cout<<i<<". "<<tokens[i]<<endl;
	}
	TITLE("Testing tokens number");		TEST(tokens.size()==4)
	TITLE("Testing tokens content 1");	TEST(tokens[0]=="123")
	TITLE("Testing tokens content 2");	TEST(tokens[1]=="123.12")
	TITLE("Testing tokens content 3");	TEST(tokens[2]=="555")
	TITLE("Testing tokens content 4");	TEST(tokens[3]=="#jhon 987")
	
	//string tests
	StringUtils::SplitStringToData(tokens, " \"Jhon Smith\"  \"Sarah O Conor\"");
	
	TITLE("Testing read string number");		TEST(tokens.size()==2)
	TITLE("Testing read string content");		TEST(tokens[0]=="Jhon Smith")
	
	//MORE COMPLEX TESTING
	StringUtils::SplitStringToData(tokens, " Jho\"n #Smith\"  \"Sarah O \\\"Conor\"#comment");
	
	//this string should be parsed to 3 tokens:
	//  Jhon #Smith
	//  Sarah O "Conor
	//  #comment
	TITLE("Testing merged strings tokens number");	TEST(tokens.size()==3)
	TITLE("Testing merged strings Jhon #Smith");	TEST(tokens[0]=="Jhon #Smith")
	TITLE("Testing quote Sarah O \"Conor");			TEST(tokens[1]=="Sarah O \"Conor")
	
	//splitting test
	//split blob from DB to tokens and data
	vector<string> outArray;
	string blob = "10|20|30|40|50|30e-2";
	StringUtils::Split(blob,outArray, "|");
	TITLE("split 10|20|30|40|50|30e-2");	TEST(outArray[5] == "30e-2")
	return true;

}
#endif //test_StringUtils_h