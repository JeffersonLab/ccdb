#ifndef test_StringUtils_h
#define test_StringUtils_h

#include "catch.hpp"

#include "CCDB/Helpers/StringUtils.h"


using namespace std;
using namespace ccdb;

TEST_CASE("CCDB/StringUtils/Split", "Test of lexical splittiong string to tokens")
{
    //Formatting tests
    
    
	//simple tokenize
	vector<string> tokens = StringUtils::LexicalSplit( " 123 123.12	555 #John 987");
	
	REQUIRE(tokens.size()==4);
	REQUIRE(tokens[0]=="123");
	REQUIRE(tokens[1]=="123.12");
	REQUIRE(tokens[2]=="555");
	REQUIRE(tokens[3]=="#John 987");
    
    
	
	//string tests
	StringUtils::LexicalSplit(tokens, " \"John Smith\"  \"Sarah O Conor\"");
	
	REQUIRE(tokens.size()==2);
	REQUIRE(tokens[0]=="John Smith");
	
	//MORE COMPLEX TESTING
	StringUtils::LexicalSplit(tokens, " Joh\"n #Smith\"  \"Sarah O \\\"Conor\"#comment");
	
	//this string should be parsed to 3 tokens:
	//  John #Smith
	//  Sarah O "Conor
	//  #comment
	REQUIRE(tokens.size()==3);
	REQUIRE(tokens[0]=="John #Smith");
	REQUIRE(tokens[1]=="Sarah O \"Conor");
	
	//splitting test
	//split blob from DB to tokens and data
	vector<string> outArray;
	string blob = "10|20|30|40|50|30e-2";
	StringUtils::Split(blob,outArray, "|");

	REQUIRE(outArray[5] == "30e-2");
}

#endif //test_StringUtils_h
