import org.jlab.ccdb.*;
import org.jlab.ccdb.JDBCProvider;

import java.util.Date;

/**
 * Created by romanov on 4/16/14.
 */
public class GetStatistics {
    public static void main(String [ ] args){

        String ccdbHome = System.getenv("CCDB_HOME");
        if(ccdbHome == null){
            System.out.println("$CCDB_HOME is not set");
            return;
        }


        JDBCProvider provider = CCDB.createProvider("sqlite:///" + ccdbHome + "/sql/ccdb.sqlite");
        provider.connect();
        provider.setDefaultVariation("subtest");

        //Enable statistics
        provider.setStatisticsIsCollecting(true);

        //read something
        Assignment data = provider.getData("/test/test_vars/test_table");
        data = provider.getData("/test/test_vars/test_table2");
        data = provider.getData("/test/test_vars/test_table");
        data = provider.getData("/test/test_vars/test_table");

        //get statistics
        RequestStatistics stat = provider.getStatistics();

        //Print what we've got here
        System.out.println("CCDB usage statistics");
        System.out.println("   Requests made:");

        for(RequestParseResult result : stat.getRequests()){
            System.out.println("      " + result.getOriginalRequest());
        }

        System.out.println();
        System.out.println("   First reading after connection takes longer [ms]: " + stat.getFirstTime() );
        System.out.println("   Total time [ms]  : " + stat.getTotalTime() );
        System.out.println("   Average time [ms]: " + stat.getAverageTime() );
        System.out.println("   Last request [ms]: " + stat.getLastRequestTime() );


    }
}
