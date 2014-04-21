import org.jlab.ccdb.*;
import org.jlab.ccdb.JDBCProvider;

import java.util.Vector;
import java.util.Date;

public class SimpleExample {

    public static void main(String [ ] args){
        JDBCProvider provider = CcdbPackage.createProvider("mysql://localhost")  ;
        provider.connect();
        Assignment asgmt = provider.getData("/test/test_vars/test_table");

        System.out.println(asgmt.getBlob());
        System.out.println(asgmt.getTypeTable().getFullPath());
        
        // gets data represented as number of columns
        for(Vector<String> row : asgmt.getStringTable()){
            for(String cell: row){
				System.out.print(cell + " ");
			}
			System.out.println(); //next line after a row
        }
    }
}
