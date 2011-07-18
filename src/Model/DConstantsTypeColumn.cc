/*
 * Column.cpp
 *
 *  Created on: Sep 28, 2010
 *      Author: romanov
 */

#include "Model/DConstantsTypeColumn.h"
#include "Model/DConstantsTypeTable.h"
namespace ccdb {

DConstantsTypeColumn::DConstantsTypeColumn( DObjectsOwner * owner/*=NULL*/, DDataProvider *provider/*=NULL*/ ):
DStoredObject(owner, provider)
{
	mId = 0;			//database table uniq id;

	mCreatedTime = 0;	//mCreatedTime time
	mModifiedTime = 0;	//mModifiedTime time
	mDBTypeTableId = 0; //gets Type table Id

	mOrder = 0;			//order of the column
	mType = DConstantsTypeColumn::cDoubleColumn;			//column type
	mTypeTable = NULL;

}



DConstantsTypeColumn::DColumnTypes DConstantsTypeColumn::StringToType( string val )
{
	if(val == "int"	) return cIntColumn	  ;
	else if(val == "uint"	) return cUIntColumn  ;
	else if(val == "long"	) return cLongColumn  ;
	else if(val == "ulong"	) return cULongColumn ;
	else if(val == "double"	) return cDoubleColumn;
	else if(val == "bool"	) return cBoolColumn  ;
	else if(val == "string"	) return cStringColumn;
	else
	{
		//TODO Warning! Wrong type
		return cDoubleColumn;
	}

}

string DConstantsTypeColumn::TypeToString( DConstantsTypeColumn::DColumnTypes val )
{
	if(val == cIntColumn   ) return string("int"	);
	else if(val == cUIntColumn  ) return string("uint"	);
	else if(val == cLongColumn  ) return string("long"	);
	else if(val == cULongColumn ) return string("ulong"	);
	else if(val == cDoubleColumn) return string("double");	
	else if(val == cBoolColumn  ) return string("bool"	);
	else if(val == cStringColumn) return string("string");	

	return string("string"); //


}

DConstantsTypeColumn::~DConstantsTypeColumn() {
	// TODO Auto-generated destructor stub
}

dbkey_t DConstantsTypeColumn::GetId() const
{
	return mId;
}

void DConstantsTypeColumn::SetId( dbkey_t val )
{
	mId = val;
}

std::string DConstantsTypeColumn::GetName() const
{
	return mName;
}

void DConstantsTypeColumn::SetName( std::string val )
{
	mName = val;
}

std::string DConstantsTypeColumn::GetComment() const
{
	return mComment;
}

void DConstantsTypeColumn::SetComment( std::string val )
{
	mComment = val;
}

time_t DConstantsTypeColumn::GetCreatedTime() const
{
	return mCreatedTime;
}

void DConstantsTypeColumn::SetCreatedTime( time_t val )
{
	mCreatedTime = val;
}

time_t DConstantsTypeColumn::GetModifiedTime() const
{
	return mModifiedTime;
}

void DConstantsTypeColumn::SetModifiedTime( time_t val )
{
	mModifiedTime = val;
}

dbkey_t DConstantsTypeColumn::GetTypeTableId() const
{
	if(mTypeTable == NULL) return mDBTypeTableId;
	return mTypeTable->GetId();
}


DConstantsTypeColumn::DColumnTypes DConstantsTypeColumn::GetType() const
{
	return mType;
}

std::string DConstantsTypeColumn::GetTypeString() const
{
	return TypeToString(mType);
}

void DConstantsTypeColumn::SetType( string val )
{
	mType = StringToType(val);
}
void DConstantsTypeColumn::SetType( DColumnTypes val )
{	
	mType = val;
}
DConstantsTypeTable * DConstantsTypeColumn::GetTypeTable() const
{
	return mTypeTable;
}

void DConstantsTypeColumn::SetTypeTable( DConstantsTypeTable * val )
{
	mTypeTable = val;
}

dbkey_t DConstantsTypeColumn::GetDBTypeTableId() const
{
	//TODO: Implement method

	return mDBTypeTableId;
}

void DConstantsTypeColumn::SetDBTypeTableId( dbkey_t val )
{
	//TODO: Implement method

	mDBTypeTableId = val;
}






} //namespace ccdb
