import org.jlab.ccdb.*;
import org.jlab.ccdb.JDBCProvider;

import java.util.Date;
import java.util.Vector;

/**
 * Created by romanov on 4/16/14.
 */
public class GetAllTables {
    public static void main(String [ ] args){

        String ccdbHome = System.getenv("CCDB_HOME");
        if(ccdbHome == null){
            System.out.println("$CCDB_HOME is not set");
            return;
        }

        System.out.println("All CCDB tables:");

        JDBCProvider provider = CCDB.createProvider("sqlite:///" + ccdbHome + "/sql/ccdb.sqlite");
        provider.connect();
        Vector<TypeTable> tables = provider.getAllTypeTables();

        for(TypeTable table : tables){
            System.out.println("      " + table.getFullPath());
        }
    }
}
