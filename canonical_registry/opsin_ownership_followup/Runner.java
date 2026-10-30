import uk.ac.cam.ch.wwmm.opsin.*;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
public class Runner {
    static String b(String s) {return Base64.getEncoder().encodeToString((s==null?"":s).getBytes(StandardCharsets.UTF_8));}
    public static void main(String[] args) {
        OpsinResult r=NameToStructure.getInstance().parseChemicalName(args[0]);
        System.out.println("VERSION\t"+NameToStructure.getVersion());
        System.out.println("STATUS\t"+r.getStatus());
        System.out.println("MESSAGE\t"+b(r.getMessage()));
        System.out.println("WARNINGS\t"+b(r.getWarnings().toString()));
        System.out.println("AMBIGUOUS\t"+r.nameAppearsToBeAmbiguous());
        System.out.println("STEREO_IGNORED\t"+r.stereochemistryIgnored());
        System.out.println("SMILES\t"+b(r.getSmiles()));
        System.out.println("CML\t"+b(r.getCml()));
    }
}
