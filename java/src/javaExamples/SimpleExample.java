import org.jlab.ccdb.*;
import org.jlab.ccdb.JDBCProvider;

import java.util.Date;

public class SimpleExample {

    public static void main(String [ ] args){
//        MySqlProvider provider = new MySqlProvider("mysql://localhost");
        JDBCProvider provider = CcdbPackage.createProvider("mysql://localhost")  ;
        provider.connect();
        Assignment asgmt = provider.getData("/test/test_vars/test_table");
//
        System.out.println(asgmt.getBlob());
        System.out.println(asgmt.getTypeTable().getFullPath());
    }
}