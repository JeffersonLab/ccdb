//
// Created by Dmitry Romanov on 11/1/2023.
// Subject to the terms in the LICENSE file found in the top-level directory.
//




bool ccdb::MySQLDataProvider::GetAssignments( vector<Assignment *> &assingments,const string& path, int runMin, int runMax, const string& runRangeName, const string& variation, time_t beginTime, time_t endTime, int sortBy/*=0*/,  int take/*=0*/, int startWith/*=0*/ )
{
    ClearErrors(); //Clear error in function that can produce new ones

    if(!CheckConnection("MySQLDataProvider::GetAssignments( ... )")) return false;

    //get table!
    ConstantsTypeTable *table = GetConstantsTypeTable(path, true);
    if(!table)
    {
        //TODO report error
        Error(CCDB_ERROR_NO_TYPETABLE,"MySQLDataProvider::GetAssignments", "Type table was not found");
        return false;
    }

    //Ok, lets cleanup result list
    if(assingments.size()>0)
    {
        vector<Assignment *>::iterator iter = assingments.begin();
        while(iter != assingments.end())
        {
            Assignment *obj = *iter;
            if(IsOwner(obj)) delete obj;    //delete objects if this provider is owner
            iter++;
        }
    }
    assingments.clear();

    //run range handle
    string runRangeWhere(""); //Where clause for run range
    if(runRangeName != "")
    {
        runRangeWhere = StringUtils::Format(" AND `runRanges`.`name` = \"%s\" ", runRangeName.c_str());
    }
    else if(runMax!=0 || runMin!=0)
    {
        runRangeWhere = StringUtils::Format(" AND `runRanges`.`runMin` <= '%i' AND `runRanges`.`runMax` >= '%i' ", runMin, runMax);
    }

    //variation handle
    string variationWhere("");
    if(variation != "")
    {
        variationWhere.assign(StringUtils::Format(" AND `variations`.`name`=\"%s\" ", variation.c_str()));
    }

    //time handle
    string timeWhere("");
    if(beginTime!=0 || endTime!=0)
    {
        timeWhere.assign(StringUtils::Format(" AND `asCreated` >= '%i' AND `asCreated` <= '%i' ", beginTime, endTime));
    }

    //limits handle
    string limitInsertion = PrepareLimitInsertion(take, startWith);

    //sort order
    string orderByInsertion(" ORDER BY `assignments`.`created` DESC ");
    if(sortBy == 1)
    {
        orderByInsertion.assign(" ORDER BY `assignments`.`created` ASC ");
    }


    //ok now we must build our mighty query...
    string query=
            /*fieldN*/  " SELECT "
                        /*00*/  " `assignments`.`id` AS `asId`,    "
                        /*01*/  " UNIX_TIMESTAMP(`assignments`.`created`) as `asCreated`,"
                        /*02*/  " UNIX_TIMESTAMP(`assignments`.`modified`) as `asModified`,    "
                        /*03*/  " `assignments`.`comment` as `asComment`, "
                        /*04*/  " `constantSets`.`id` AS `constId`, "
                        /*05*/  " `constantSets`.`vault` AS `blob`, "
                        /*06*/  " `runRanges`.`id`   AS `rrId`, "
                        /*07*/  " UNIX_TIMESTAMP(`runRanges`.`created`) as `rrCreated`,"
                        /*08*/  " UNIX_TIMESTAMP(`runRanges`.`modified`) as `rrModified`,    "
                        /*09*/  " `runRanges`.`name`   AS `rrName`, "
                        /*10*/  " `runRanges`.`runMin`   AS `rrMin`, "
                        /*11*/  " `runRanges`.`runMax`   AS `runMax`, "
                        /*12*/  " `runRanges`.`comment` as `rrComment`, "
                        /*13*/  " `variations`.`id`  AS `varId`, "
                        /*14*/  " UNIX_TIMESTAMP(`variations`.`created`) as `varCreated`,"
                        /*15*/  " UNIX_TIMESTAMP(`variations`.`modified`) as `varModified`,    "
                        /*16*/  " `variations`.`name` AS `varName`, "
                        /*17*/  " `variations`.`comment`  AS `varComment` "
                        " FROM `runRanges` "
                        " INNER JOIN `assignments` ON `assignments`.`runRangeId`= `runRanges`.`id`"
                        " INNER JOIN `variations` ON `assignments`.`variationId`= `variations`.`id`    "
                        " INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id`"
                        " INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id`"
                        " WHERE  `typeTables`.`id` = '%i' %s %s %s %s %s";


    query=StringUtils::Format(query.c_str(), table->GetId(), runRangeWhere.c_str(), variationWhere.c_str(), timeWhere.c_str(), orderByInsertion.c_str(), limitInsertion.c_str());
    //query this
    if(!QuerySelect(query))
    {
        //TODO report error
        return false;
    }

    //Ok! We querried our run range! lets catch it!
    while(FetchRow())
    {
        assingments.push_back(FetchAssignment(table));

    }

    FreeMySQLResult();

    return true;
}

bool ccdb::MySQLDataProvider::GetAssignments(vector<Assignment*>& assingments, const string& path, int run, const string& variation, time_t date, int take, int startWith)
{
    return GetAssignments(assingments, path, run, run,"",variation, 0, date, take, startWith);
}

vector<Assignment *> ccdb::MySQLDataProvider::GetAssignments( const string& path, int run, const string& variation/*=""*/, time_t date/*=0*/, int take/*=0*/, int startWith/*=0*/ )
{
    vector<Assignment *> assingments;
    GetAssignments(assingments, path, run,variation, date, take, startWith);
    return assingments;
}

bool ccdb::MySQLDataProvider::GetAssignments( vector<Assignment *> &assingments,const string& path, const string& runName, const string& variation/*=""*/, time_t date/*=0*/, int take/*=0*/, int startWith/*=0*/ )
{
    return GetAssignments(assingments, path, 0, 0,runName,variation, 0, date, take, startWith);
}

vector<Assignment *> ccdb::MySQLDataProvider::GetAssignments( const string& path, const string& runName, const string& variation/*=""*/, time_t date/*=0*/, int take/*=0*/, int startWith/*=0*/ )
{
    vector<Assignment *> assingments;
    GetAssignments(assingments, path, runName,variation, date, take, startWith);
    return assingments;
}



bool ccdb::MySQLDataProvider::FillAssignment(Assignment* assignment)
{
    ClearErrors(); //Clear error in function that can produce new ones
    if(assignment == nullptr || !assignment->GetId())
    {
        //TODO report errors
        Error(CCDB_ERROR_ASSIGMENT_INVALID,"MySQLDataProvider::FillAssignment", "ASSIGnMENt is nullptr or has improper ID so update operations cant be done");
        return false;
    }

    //ok now we must build our mighty query...
    string query=
            /*fieldN*/  " SELECT "
                        /*00*/  " `assignments`.`id` AS `asId`,    "
                        /*01*/  " UNIX_TIMESTAMP(`assignments`.`created`) as `asCreated`,"
                        /*02*/  " UNIX_TIMESTAMP(`assignments`.`modified`) as `asModified`,    "
                        /*03*/  " `assignments`.`comment` as `asComment`, "
                        /*04*/  " `constantSets`.`id` AS `constId`, "
                        /*05*/  " `constantSets`.`vault` AS `blob`, "
                        /*06*/  " `runRanges`.`id`   AS `rrId`, "
                        /*07*/  " UNIX_TIMESTAMP(`runRanges`.`created`) as `rrCreated`,"
                        /*08*/  " UNIX_TIMESTAMP(`runRanges`.`modified`) as `rrModified`,    "
                        /*09*/  " `runRanges`.`name`   AS `rrName`, "
                        /*10*/  " `runRanges`.`runMin`   AS `rrMin`, "
                        /*11*/  " `runRanges`.`runMax`   AS `runMax`, "
                        /*12*/  " `runRanges`.`comment` as `rrComment`, "
                        /*13*/  " `variations`.`id`  AS `varId`, "
                        /*14*/  " UNIX_TIMESTAMP(`variations`.`created`) as `varCreated`,"
                        /*15*/  " UNIX_TIMESTAMP(`variations`.`modified`) as `varModified`,    "
                        /*16*/  " `variations`.`name` AS `varName`, "
                        /*17*/  " `variations`.`comment`  AS `varComment`, "
                        /*18*/  " `typeTables`.`name` AS `typeTableName`, "
                        /*19*/  " `directories`.`id` AS `dirId` "
                        " FROM `runRanges` "
                        " INNER JOIN `assignments` ON `assignments`.`runRangeId`= `runRanges`.`id`"
                        " INNER JOIN `variations` ON `assignments`.`variationId`= `variations`.`id`    "
                        " INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id`"
                        " INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id`"
                        " INNER JOIN `directories` ON `typeTables`.`directoryId` = `directories`.`id`"
                        " WHERE  `assignments`.`id` = '%i'";


    query=StringUtils::Format(query.c_str(), assignment->GetId());
    //cout << query<<endl;
    //query this
    if(!QuerySelect(query))
    {
        //TODO report error
        cout<<"!QuerySelect(query)"<<endl;
        return false;
    }

    if(!FetchRow())
    {
        //TODO report error
        cout<<"no assignment selected!"<<endl;
        return false;
    }

    //fetch readed row
    FetchAssignment(assignment, assignment->GetTypeTable());

    //Ok! Here is a tricky moment. We should load a constant type table
    //but we have an API that allows us to load such directories by name
    //The problem that we should know a full path of it.
    //So we pulled a directory ID and data table name.
    // We have a list of directories by their ID thus we will know a full path
    // of type table.
    // lets make this plan work

    string typeTableName = ReadString(18);
    dbkey_t directoryId = ReadIndex(19);

    //maybe we need to update our directories?
    UpdateDirectoriesIfNeeded();

    if(mDirectoriesById.find(directoryId) == mDirectoriesById.end())
    {
        //TODO report errors
        Error(CCDB_ERROR,"MySQLDataProvider::FillAssignment", "Cannot find directory locally by ID taken from database");
        return false;
    }

    Directory *parent = mDirectoriesById[directoryId];

    ConstantsTypeTable * table = GetConstantsTypeTable(typeTableName, parent, true);
    if(!table)
    {
        Error(CCDB_ERROR_NO_TYPETABLE,"MySQLDataProvider::FillAssignment", "Type table was not loaded");
        return false;
    }

    assignment->SetTypeTable(table);
    table->SetOwner(assignment);

    FreeMySQLResult();

    return true;
}



std::string ccdb::MySQLDataProvider::PrepareCommentForInsert( const string& comment )
{
    // The idea is that we have to place
    // (..., nullptr) in INSERT queries if comment is nullptr
    // and (..., "<content>") if it is not nullptr
    // So this function returns string containing nullptr or \"<comment content>\"


    if(comment.length() == 0)
    {
        // we put empty comments as nullptr
        //because comments uses "TEXT" field that takes additional size
        // if text field in DB is nullptr it will be read as "" by ReadString()
        // so it is safe to do this

        return string("nullptr");
    }
    else
    {
        string commentIns ="\"";
        commentIns.append(comment);
        commentIns.append("\"");
        return commentIns;
    }

}


bool ccdb::MySQLDataProvider::QueryCustom( const string& query )
{
    if(!CheckConnection("MySQLDataProvider::QueryCustom")) return false;

    //do we have some results we need to free?
    if(mResult!=nullptr)
    {
        FreeMySQLResult();
    }
    //query
    if(mysql_query(mMySQLHnd, query.c_str()))
    {
        string errStr = ComposeMySQLError("mysql_query()"); errStr.append("\n Query: "); errStr.append(query);
        Error(CCDB_ERROR_MYSQL_CUSTOM_QUERY,"ccdb::MySQLDataProvider::QueryCustom( string query )",errStr.c_str());
        return false;
    }
    return true;
}



dbkey_t ccdb::MySQLDataProvider::GetUserId( string userName )
{
    if(userName == "" || !ValidateName(userName))
    {
        return 1; //anonymous id
    }

    string query = "SELECT `id` FROM `authors` WHERE `name` = \"" + userName + "\" LIMIT 0,1");
    if(!QuerySelect(query))
    {
        return 1; //anonymous id
    }


    if(!FetchRow())
    {
        return 1; //anonymous id
    }

    dbkey_t id = ReadIndex(0);

    FreeMySQLResult();

    if(id<=0) return 1;
    return id;
}





int ccdb::MySQLDataProvider::CountConstantsTypeTables(Directory *dir)
{
    /**
     * @brief This function counts number of type tables for a given directory
     * @param [in] directory to look tables in
     * @return number of tables to return
     */
    return 0;
}



bool ccdb::MySQLDataProvider::GetRunRanges(vector<RunRange*>& resultRunRanges, ConstantsTypeTable* table, const string& variation/*=""*/, int take/*=0*/, int startWith/*=0*/)
{
    CheckConnection("MySQLDataProvider::GetRunRanges(vector<DRunRange*>& resultRunRanges, ConstantsTypeTable* table, int take, int startWith)");

    //validate table
    if(!table || !table->GetId())
    {
        //TODO report error
        Error(CCDB_ERROR_NO_TYPETABLE,"MySQLDataProvider::GetRunRanges", "Type table is null or have invalid id");
        return false;
    }
    //variation handle
    string variationWhere("");
    if(variation != "")
    {
        variationWhere.assign(" AND `variations`.`name`=\"" + variation + "\" ");
    }

    //limits handle
    string limitInsertion = PrepareLimitInsertion(take, startWith);

    //Ok, lets cleanup result list
    if(resultRunRanges.size()>0)
    {
        vector<RunRange *>::iterator iter = resultRunRanges.begin();
        while(iter != resultRunRanges.end())
        {
            RunRange *obj = *iter;
            iter++;
        }
    }
    resultRunRanges.clear(); //we clear the consts. Considering that some one else should handle deletion


    //ok now we must build our mighty query...
    string query=
            " SELECT "
            " DISTINCT `runRanges`.`id` as `id`, "
            " UNIX_TIMESTAMP(`runRanges`.`created`) as `created`, "
            " UNIX_TIMESTAMP(`runRanges`.`modified`) as `modified`, "
            " `runRanges`.`name` as `name`, "
            " `runRanges`.`runMin` as `runMin`, "
            " `runRanges`.`runMax` as `runMax`, "
            "`runRanges`.`comment` as `comment` "
            " FROM `typeTables` "
            " INNER JOIN `assignments` ON `assignments`.`runRangeId`= `runRanges`.`id` "
            " INNER JOIN `variations` ON `assignments`.`variationId`= `variations`.`id` "
            " INNER JOIN `constantSets` ON `assignments`.`constantSetId` = `constantSets`.`id` "
            " INNER JOIN `typeTables` ON `constantSets`.`constantTypeId` = `typeTables`.`id` "
            " WHERE `typeTables`.`id` = '" + to_string(table->GetId()) + "' "
            + variationWhere +
            " ORDER BY `runRanges`.`runMin` ASC " + limitInsertion;

    //query this
    if(!QuerySelect(query))
    {
        //TODO report error
        return false;
    }

    //Ok! We querried our run range! lets catch it!
    while(FetchRow())
    {
        //ok lets read the data...
        RunRange *result = new RunRange();
        result->SetId(ReadULong(0));
        result->SetCreatedTime(ReadUnixTime(1));
        result->SetModifiedTime(ReadUnixTime(2));
        result->SetName(ReadString(3));
        result->SetMin(ReadInt(4));
        result->SetMax(ReadInt(5));
        result->SetComment(ReadString(7));

        resultRunRanges.push_back(result);
    }

    FreeMySQLResult();
    return true;
}