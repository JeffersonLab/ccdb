import org.jlab.ccdb.*;
import org.jlab.ccdb.JDBCProvider;

import java.util.Date;
import java.util.List;
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
            //Get columns
            List<TypeTableColumn> columns = table.getColumns();

            // Get table full path
            String fullPath = table.getFullPath();

            // print...
            System.out.println ("      " + fullPath + " columns: " + columnsToString(columns, 3));
        }
    }


    public static String columnsToString( List<TypeTableColumn> columns, int columnsToShow) {

        String result = "[";

        for (int i = 0; i < Math.max(columnsToShow, columns.size()); i++) {
            TypeTableColumn column = columns.get(i);
            if(i!=0) result += ", ";
            result += column.getName() + "(" + column.getCellType() + ")";
        }
        if(columnsToShow < columns.size()) {
            result += (", ...]");
        }
        else {
            result += ("]");
        }
        return result;
    }
}
