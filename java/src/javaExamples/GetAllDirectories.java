import org.jlab.ccdb.CCDB;
import org.jlab.ccdb.Directory;
import org.jlab.ccdb.JDBCProvider;

public class GetAllDirectories {
    public static void main(String [ ] args){

        String ccdbHome = System.getenv("CCDB_HOME");
        if(ccdbHome == null){
            System.out.println("$CCDB_HOME is not set");
            return;
        }

        System.out.println("Directories for two levels");

        // Connect to database
        JDBCProvider provider = CCDB.createProvider("sqlite:///" + ccdbHome + "/sql/ccdb.sqlite");
        provider.connect();

        // 'root' directory is '/' (it is not stored database)
        Directory root = provider.getRootDir();

        // iterate over directories
        for(Directory dir : root.getSubdirectories()){
            System.out.println(dir.getFullPath());
            for(Directory subDir : dir.getSubdirectories()){
                System.out.println("      " + subDir.getFullPath());
            }
        }
    }
}
