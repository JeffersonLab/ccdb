import org.ccdb.CalibrationProvider;
import org.ccdb.model.Directory;

public class SimpleExample {

    public static void main(String [ ] args){
        CalibrationProvider provider = new CalibrationProvider();
        provider.connect();
        Directory dir = provider.getDirectory("/test");
        System.out.println("Hello World! " + dir.getId());

    }
}