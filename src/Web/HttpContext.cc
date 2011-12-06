
#pragma warning(disable: 4996)

#include <iostream>
#include <stdio.h>
#include <string.h>
#include "Web/ConfigReader.h"
#include "Web/HttpContext.h"
#include "CCDB/Providers/DataProvider.h"
#include "CCDB/Providers/MySQLDataProvider.h"
#include "CCDB/Model/Directory.h"
#include "CCDB/Log.h"

using namespace std;
using namespace ccdb;

// Global static pointer used to ensure a single instance of the class.
HttpContext* ccdb::HttpContext::mInstance = NULL; 
	
/** This function is called to create an instance of the class.
Calling the constructor publicly is not allowed. The constructor
is private and is only called by this Instance function.
*/
HttpContext* ccdb::HttpContext::Instance()
{
   if (!mInstance)   // Only allow one instance of class to be generated.
	  mInstance = new HttpContext();
   return mInstance;
}


ccdb::HttpContext::HttpContext()
{
	InitializeGet(mGet);
	InitializePost(mPost);
	mConnectionString = "None";
	ConfigReader reader("ccdb.inp");	
	reader.readInto(mConnectionString, "ConnectionString");
	Log::SetUseColors(false);
	
}


void ccdb::HttpContext::ProcessRequest()
{
	//TODO: Implement method
	cout<<"Content-Type: text/html"<<endl<<endl;
	//cout<<"{\"path\":\"/test/test_table\", \"comment\":\"This is a type table for software testing\"}"<<endl;
	/*cout<<"[";
	map<string,string>::iterator iter=mGet.begin();
	while(iter!=mGet.end())
	{
		cout<<"{ \"text\": \""<< iter->first <<" -> "<< iter->second <<"\"}"; 
		++iter;
		if(iter!=mGet.end()) cout<<","<<endl;
	}
	cout<<"]";*/
	//if(mGet.find("root")!=mGet.end()) cout<<mGet["root"]<<endl; 
	//if(mPost.find("root")!=mPost.end()) cout<<mPost["root"]<<endl; 
	string operation = (mGet.find("op")!=mGet.end())? mGet["op"] : "";
	
	if(operation == "ajaxdirs")
	{
		OpAjaxDirectoryList();
	}
	else
	{
		cout<<"no operation specified"<<endl;
	}
	

	/*
	if(mGet.find("root")!=mGet.end() || mPost.find("root")!=mPost.end())
	{
		cout<<
			"[{"
			"	\"text\": \"1. Pre Lunch (120 min)\","
			"	\"expanded\": true,"
			"	\"classes\": \"important\","
			"	\"children\":"
			"	["
			"		{"
			"			\"text\": \"1.1 The State of the Powerdome (30 min)\""
			"		},"
			"	 	{"
			"			\"text\": \"1.2 The Future of jQuery (30 min)\""
			"		},"
			"	 	{"
			"			\"text\": \"1.2 jQuery UI - A step to richnessy (60 min)\""
			"		}"
			"	]"
			"},"
			"{"
			"	\"text\": \"2. Lunch  (60 min)\""
			"}]"<<endl;
	}*/
	

}

void ccdb::HttpContext::OpAjaxDirectoryList()
{
	DataProvider *prov = new MySQLDataProvider();
	
	if(!prov->Connect(mConnectionString))
	{
		cout<<"error connect"<<endl;
	}
	
	vector<Directory *> dirs;// = prov->SearchDirectories("*", "/");
	string rootDir="/";
	if(mGet.find("root")!=mGet.end() && mGet["root"]!="source")
	{
		 rootDir = mGet["root"];
	}
	
	prov->SearchDirectories(dirs, "*", rootDir);
	
	if(dirs.size()>0)
	{
		cout<<"[";
		for(int i=0; i<dirs.size(); i++)		
		{
			string hasChildren=(dirs[i]->GetSubdirectories().size()>0)?"true":"false";
			cout<<"{ \"text\": \""<< dirs[i]->GetName() <<"\", \"id\": \""<<dirs[i]->GetFullPath()<<"\",\"hasChildren\": "<<hasChildren<<"}";
			if(i!=dirs.size()-1) cout<<","<<endl;
		}
		cout<<"]";
	}
	
	delete prov;
}

void ccdb::HttpContext::InitializePost( std::map <std::string, std::string> &Post )
{
	//TODO: Implement method

	std::string tmpkey, tmpvalue;
	std::string *tmpstr = &tmpkey;
	int content_length;
	register char *ibuffer;
	char *buffer = NULL;
	char *strlength = getenv("CONTENT_LENGTH");
	if (strlength == NULL) {
		Post.clear();
		return;
	}
	content_length = atoi(strlength);
	if (content_length == 0) {
		Post.clear();
		return;
	}

	try {
		buffer = new char[content_length*sizeof(char)];
	} catch (std::bad_alloc xa) {
		Post.clear();
		return;
	}
	if(fread(buffer, sizeof(char), content_length, stdin) != (unsigned int)content_length) {
		Post.clear();
		return;
	}
	*(buffer+content_length) = '\0';
	ibuffer = buffer;
	while (*ibuffer != '\0') {
		if (*ibuffer=='&') {
			if (tmpkey!="") {
				Post[UrlDecode(tmpkey)] = UrlDecode(tmpvalue);
			}
			tmpkey.clear();
			tmpvalue.clear();
			tmpstr = &tmpkey;
		} else if (*ibuffer=='=') {
			tmpstr = &tmpvalue;
		} else {
			(*tmpstr) += (*ibuffer);
		}
		ibuffer++;
	}
	//enter the last pair to the map
	if (tmpkey!="") {
		Post[UrlDecode(tmpkey)] = UrlDecode(tmpvalue);
		tmpkey.clear();
		tmpvalue.clear();
	}
}

void ccdb::HttpContext::InitializeGet( std::map <std::string, std::string> &values )
{
	//TODO: Implement method

	std::string tmpkey, tmpvalue;
	std::string *tmpstr = &tmpkey;

	register char* raw_get = getenv("QUERY_STRING");
	values.clear();
	if (raw_get==NULL) 
	{

		return;
	}
	//lets iterate through values
	while (*raw_get != '\0') 
	{
		//have we reach the next value?
		if (*raw_get=='&') 
		{
			if (tmpkey!="") 
			{
				values[UrlDecode(tmpkey)] = UrlDecode(tmpvalue);
			}
			tmpkey.clear();
			tmpvalue.clear();
			tmpstr = &tmpkey;
		} 
		else if (*raw_get=='=') //Have ve reached a key value change?
		{
			tmpstr = &tmpvalue;
		} 
		else 
		{
			(*tmpstr) += (*raw_get);
		}
		raw_get++;
	}
	//enter the last pair to the map
	if (tmpkey!="") 
	{
		values[UrlDecode(tmpkey)] = UrlDecode(tmpvalue);
		tmpkey.clear();
		tmpvalue.clear();
	}
}

std::string ccdb::HttpContext::UrlDecode( const string& str )
{
	//TODO: Implement method

	register int i;
	string temp;
	char tmp[5], tmpchar;
	
	strcpy(tmp,"0x");
	int size = str.size();
	for (i=0; i<size; i++) 
	{
		if (str[i]=='%') 
		{
			if (i+2<size) 
			{
				tmp[2] = str[i+1];
				tmp[3] = str[i+2];
				tmp[4] = '\0';

				tmpchar = (char)strtol(tmp,NULL,0);

				temp+=tmpchar;
				i += 2;
				continue;
			} 
			else 
			{
				break;
			}
		} 
		else if (str[i]=='+') 
		{
			temp+=' ';
		} 
		else 
		{
			temp+=str[i];
		}
	}
	return temp;
}

void ccdb::HttpContext::PrintVariables()
{
	
	//TODO: Implement method
	
	for (map<string,string>::iterator iter=mGet.begin(); iter!=mGet.end(); ++iter)
	{
		cout<< iter->first <<" -> "<< iter->second <<" <br/> "<<endl; 
	}
	

}

void ccdb::HttpContext::ProcessOperation()
{
}

void ccdb::HttpContext::RenderResponse()
{
}

void ccdb::HttpContext::WriteResponse(const string& content)
{
}


