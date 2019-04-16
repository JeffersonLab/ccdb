import org.jlab.ccdb.*;
import org.jlab.ccdb.JDBCProvider;

import java.util.Vector;

public class SimpleExample {

    public static void main(String [ ] args){
        JDBCProvider provider = CCDB.createProvider("mysql://hallddb.jlab.org")  ;
        provider.connect();

        //to check the table exists
        System.out.println("/test/test_vars/test_table exists? - " + provider.isTypeTableAvailable("/test/test_vars/test_table"));

        //get data
        Assignment asgmt = provider.getData("/test/test_vars/test_table");
        
        // gets data represented as number rows and columns
        for(Vector<Double> row : asgmt.getTableDouble()){
            for(Double cell: row){
				System.out.print(cell + " ");
			}
			System.out.println(); //next line after a row
        }

        Vector<String> valuesByColumn = asgmt.getColumnValuesString("x");
        System.out.println("Values in column 'x':");
        System.out.println(valuesByColumn);

        Vector<Double> doubleValues = asgmt.getColumnValuesDouble(1);
        System.out.println("Double values in second column:");
        System.out.println(doubleValues);

        //gets some extended info about data
        System.out.println(asgmt.getTypeTable().getFullPath());

        //This table doesn't exists
        System.out.println("/test/test_vars/evil_table exists? - " + provider.isTypeTableAvailable("/test/test_vars/evil_table"));
    }
}
