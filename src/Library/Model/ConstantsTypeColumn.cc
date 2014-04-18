/*
 * Column.cpp
 */

#include "CCDB/Model/ConstantsTypeColumn.h"
#include "CCDB/Model/ConstantsTypeTable.h"

namespace ccdb {

ConstantsTypeColumn::ConstantsTypeColumn( ObjectsOwner * owner/*=NULL*/, DataProvider *provider/*=NULL*/ ):
StoredObject(owner, provider)
{
	mId = 0;			//database table uniq id;

	mCreatedTime = 0;	//mCreatedTime time
	mModifiedTime = 0;	//mModifiedTime time
	mDBTypeTableId = 0; //gets Type table Id

	mOrder = 0;			//order of the column
	mType = ConstantsTypeColumn::cDoubleColumn;			//column type
	mTypeTable = NULL;

}



ConstantsTypeColumn::ColumnTypes ConstantsTypeColumn::StringToType( string val )
{
	if(val == "int"	) return cIntColumn;
	else if (val == "uint") return cUIntColumn;
	else if(val == "long"	) return cLongColumn;
	else if(val == "ulong"	) return cULongColumn;
	else if(val == "double"	) return cDoubleColumn;
	else if(val == "bool"	) return cBoolColumn;
	else if(val == "string"	) return cStringColumn;
	else
	{
		//TODO Warning! Wrong type
		return cDoubleColumn;
	}

}

string ConstantsTypeColumn::TypeToString( ConstantsTypeColumn::ColumnTypes val )
{
	if(val == cIntColumn   ) return string("int");
	else if(val == cUIntColumn  ) return string("uint");
	else if(val == cLongColumn  ) return string("long");
	else if(val == cULongColumn ) return string("ulong");
	else if(val == cDoubleColumn) return string("double");	
	else if(val == cBoolColumn  ) return string("bool");
	else if(val == cStringColumn) return string("string");	

	return string("string"); //


}

ConstantsTypeColumn::~ConstantsTypeColumn() {
	// TODO Auto-generated destructor stub
}

dbkey_t ConstantsTypeColumn::GetId() const
{
	return mId;
}

void ConstantsTypeColumn::SetId( dbkey_t val )
{
	mId = val;
}

std::string ConstantsTypeColumn::GetName() const
{
	return mName;
}

void ConstantsTypeColumn::SetName( std::string val )
{
	mName = val;
}

std::string ConstantsTypeColumn::GetComment() const
{
	return mComment;
}

void ConstantsTypeColumn::SetComment( std::string val )
{
	mComment = val;
}

time_t ConstantsTypeColumn::GetCreatedTime() const
{
	return mCreatedTime;
}

void ConstantsTypeColumn::SetCreatedTime( time_t val )
{
	mCreatedTime = val;
}

time_t ConstantsTypeColumn::GetModifiedTime() const
{
	return mModifiedTime;
}

void ConstantsTypeColumn::SetModifiedTime( time_t val )
{
	mModifiedTime = val;
}

dbkey_t ConstantsTypeColumn::GetTypeTableId() const
{
	if(mTypeTable == NULL) return mDBTypeTableId;
	return mTypeTable->GetId();
}


ConstantsTypeColumn::ColumnTypes ConstantsTypeColumn::GetType() const
{
	return mType;
}

std::string ConstantsTypeColumn::GetTypeString() const
{
	return TypeToString(mType);
}

void ConstantsTypeColumn::SetType( string val )
{
	mType = StringToType(val);
}
void ConstantsTypeColumn::SetType( ColumnTypes val )
{	
	mType = val;
}
ConstantsTypeTable * ConstantsTypeColumn::GetTypeTable() const
{
	return mTypeTable;
}

void ConstantsTypeColumn::SetTypeTable( ConstantsTypeTable * val )
{
	mTypeTable = val;
}

dbkey_t ConstantsTypeColumn::GetDBTypeTableId() const
{
	//TODO: Implement method

	return mDBTypeTableId;
}

void ConstantsTypeColumn::SetDBTypeTableId( dbkey_t val )
{
	//TODO: Implement method

	mDBTypeTableId = val;
}






} //namespace ccdb
