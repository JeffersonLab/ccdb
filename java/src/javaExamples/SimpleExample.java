import org.jlab.ccdb.*;
import org.jlab.ccdb.JDBCProvider;

import java.util.Vector;

public class SimpleExample {

    public static void main(String [ ] args){
        JDBCProvider provider = CcdbPackage.createProvider("mysql://localhost")  ;
        provider.connect();
        Assignment asgmt = provider.getData("/test/test_vars/test_table");
        
        // gets data represented as number of columns
        for(Vector<String> row : asgmt.getTableString()){
            for(String cell: row){
				System.out.print(cell + " ");
			}
			System.out.println(); //next line after a row
        }

        Vector<String> valuesByColumn = asgmt.getColumnValuesString("x");
        System.out.println("Values in column 'x':");
        System.out.println(valuesByColumn);

        valuesByColumn = asgmt.getColumnValuesString(1);
        System.out.println("Values in second column:");
        System.out.println(valuesByColumn);

        //gets some extended info about data
        System.out.println(asgmt.getTypeTable().getFullPath());
    }
}
