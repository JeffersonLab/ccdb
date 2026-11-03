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

// The StringUtils API is used by software that links libccdb, so every function keeps its signature and its results;
// these cases pin them (2.5 rewrote the implementations with standard functions).

TEST_CASE("CCDB/StringUtils/IntToString", "[StringUtils]")
{
    REQUIRE(StringUtils::IntToString(0) == "0");
    REQUIRE(StringUtils::IntToString(42) == "42");
    REQUIRE(StringUtils::IntToString(-42) == "-42");
    REQUIRE(StringUtils::IntToString(2147483647) == "2147483647");
    REQUIRE(StringUtils::IntToString(-2147483647 - 1) == "-2147483648");
    REQUIRE(StringUtils::IntToString(5, 2) == "101");
    REQUIRE(StringUtils::IntToString(255, 16) == "ff");
    REQUIRE(StringUtils::IntToString(-255, 16) == "-ff");
    REQUIRE(StringUtils::IntToString(35, 36) == "z");
    REQUIRE(StringUtils::IntToString(8, 8) == "10");
    REQUIRE(StringUtils::IntToString(-2147483647 - 1, 2) == "-10000000000000000000000000000000");
    REQUIRE(StringUtils::IntToString(7, 1).empty());
    REQUIRE(StringUtils::IntToString(7, 37).empty());
}


TEST_CASE("CCDB/StringUtils/Parse values", "[StringUtils]")
{
    REQUIRE(StringUtils::ParseInt("42") == 42);
    REQUIRE(StringUtils::ParseInt(" 42") == 42);
    REQUIRE(StringUtils::ParseInt("-7") == -7);
    REQUIRE(StringUtils::ParseInt("+7") == 7);
    REQUIRE(StringUtils::ParseInt("12abc") == 12);
    REQUIRE(StringUtils::ParseInt("abc") == 0);
    REQUIRE(StringUtils::ParseInt("") == 0);
    REQUIRE(StringUtils::ParseInt("1.9") == 1);
    REQUIRE(StringUtils::ParseUInt("42") == 42u);
    REQUIRE(StringUtils::ParseLong("-9000000000") == -9000000000L);
    REQUIRE(StringUtils::ParseULong("9000000000") == 9000000000UL);
    REQUIRE(StringUtils::ParseUnixTime("1709296215") == 1709296215);
    REQUIRE(StringUtils::ParseDouble("1.5") == 1.5);
    REQUIRE(StringUtils::ParseDouble("1e-3") == 0.001);
    REQUIRE(StringUtils::ParseDouble(" 2.5") == 2.5);
    REQUIRE(StringUtils::ParseDouble("abc") == 0.0);
    REQUIRE(StringUtils::ParseDouble("0.1") == 0.1);
    REQUIRE(StringUtils::ParseBool("true"));
    REQUIRE_FALSE(StringUtils::ParseBool("false"));
    REQUIRE(StringUtils::ParseBool("1"));
    REQUIRE(StringUtils::ParseBool("2"));
    REQUIRE_FALSE(StringUtils::ParseBool("0"));
    REQUIRE_FALSE(StringUtils::ParseBool("x"));
    REQUIRE(StringUtils::ParseString("a b") == "a b");
}


TEST_CASE("CCDB/StringUtils/Parse success flag", "[StringUtils]")
{
    // The flag says whether the whole text, blanks around it aside, was a number in range
    bool ok = false;
    REQUIRE(StringUtils::ParseInt("42", &ok) == 42);
    REQUIRE(ok);
    REQUIRE(StringUtils::ParseInt(" 42 ", &ok) == 42);
    REQUIRE(ok);
    StringUtils::ParseInt("12abc", &ok);
    REQUIRE_FALSE(ok);
    StringUtils::ParseInt("", &ok);
    REQUIRE_FALSE(ok);
    StringUtils::ParseInt("99999999999", &ok);
    REQUIRE_FALSE(ok);
    StringUtils::ParseDouble("1.5x", &ok);
    REQUIRE_FALSE(ok);
    REQUIRE(StringUtils::ParseDouble("-1.5e2", &ok) == -150.0);
    REQUIRE(ok);
    StringUtils::ParseBool("maybe", &ok);
    REQUIRE_FALSE(ok);
    REQUIRE(StringUtils::ParseBool("true", &ok));
    REQUIRE(ok);
    REQUIRE(StringUtils::ParseULong("18446744073709551615", &ok) == 18446744073709551615UL);
    REQUIRE(ok);
}


TEST_CASE("CCDB/StringUtils/Replace, Split, Trim", "[StringUtils]")
{
    string out;
    REQUIRE(StringUtils::Replace("ab", "x", "abcabab", out) == 3);
    REQUIRE(out == "xcxx");
    REQUIRE(StringUtils::Replace("a", "aa", "aba") == "aabaa");
    REQUIRE(StringUtils::Replace("calibtime=", "", "calibtime=2024") == "2024");
    REQUIRE(StringUtils::Replace("zz", "x", "abc") == "abc");

    vector<string> parts = StringUtils::Split("  a  b c ");
    REQUIRE(parts == vector<string>({"a", "b", "c"}));
    REQUIRE(StringUtils::Split("1|2||3", "|") == vector<string>({"1", "2", "3"}));
    REQUIRE(StringUtils::Split("").empty());

    string text = " \t value \r\n";
    StringUtils::Trim(text);
    REQUIRE(text == "value");
    string blank = " \t ";
    StringUtils::Trim(blank);
    REQUIRE(blank.empty());
}


TEST_CASE("CCDB/StringUtils/WildCardCheck", "[StringUtils]")
{
    REQUIRE(StringUtils::WildCardCheck("*.txt", "a.txt"));
    REQUIRE_FALSE(StringUtils::WildCardCheck("*.txt", "a.txt2"));
    REQUIRE(StringUtils::WildCardCheck("a?c", "abc"));
    REQUIRE_FALSE(StringUtils::WildCardCheck("a?c", "ac"));
    REQUIRE(StringUtils::WildCardCheck("a*c", "abbbc"));
    REQUIRE_FALSE(StringUtils::WildCardCheck("a*c", "abd"));
    REQUIRE(StringUtils::WildCardCheck("*", ""));
    REQUIRE(StringUtils::WildCardCheck("", ""));
    REQUIRE_FALSE(StringUtils::WildCardCheck("", "a"));
    REQUIRE(StringUtils::WildCardCheck("*a*b*", "xxaxxbxx"));
    REQUIRE(StringUtils::WildCardCheck("t*_*", "test_table"));
    REQUIRE_FALSE(StringUtils::WildCardCheck("t*_*", "testtable"));
}


TEST_CASE("CCDB/StringUtils/Encode and Decode", "[StringUtils]")
{
    REQUIRE(StringUtils::Encode("a & <b> \"c\"") == "a &amp; &lt;b&gt; &quot;c&quot;");
    REQUIRE(StringUtils::Decode("a &amp; &lt;b&gt; &quot;c&quot;") == "a & <b> \"c\"");
    REQUIRE(StringUtils::Decode(StringUtils::Encode("x &amp; y")) == "x &amp; y");
    // text without entities stays as it is (2.4 turned any of the characters of "&amp;" into "&": "map" became "&")
    REQUIRE(StringUtils::Decode("map & pal; lamp") == "map & pal; lamp");
}


TEST_CASE("CCDB/StringUtils/MaskPassword", "[StringUtils]")
{
    REQUIRE(StringUtils::MaskPassword("mysql://user:secret@host/db") == "mysql://user:***@host/db");
    REQUIRE(StringUtils::MaskPassword("mysql://user:p@ss@host/db") == "mysql://user:***@host/db");
    REQUIRE(StringUtils::MaskPassword("mysql://user@host/db") == "mysql://user@host/db");
    REQUIRE(StringUtils::MaskPassword("sqlite:////tmp/a.sqlite") == "sqlite:////tmp/a.sqlite");
}

#endif //test_StringUtils_h
