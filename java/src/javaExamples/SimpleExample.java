import org.ccdb.DatabaseProvider;
import org.ccdb.MySqlProvider;
import org.ccdb.model.Directory;

public class SimpleExample {

    public static void main(String [ ] args){
        MySqlProvider provider = new MySqlProvider();
        provider.connect("mysql://localhost");
        Directory dir = provider.getDirectory("/test");
        System.out.println("Hello World! " + dir.getId());
    }
}