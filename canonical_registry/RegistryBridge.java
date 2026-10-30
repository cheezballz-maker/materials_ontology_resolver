import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import uk.ac.cam.ch.wwmm.opsin.*;
import io.github.dan2097.jnainchi.*;

/** Line-oriented, base64 fields preserve exact queries, warnings and structures. */
public class RegistryBridge {
  static String b(String s) {return Base64.getEncoder().encodeToString((s==null?"":s).getBytes(StandardCharsets.UTF_8));}
  public static void main(String[] args) throws Exception {
    BufferedReader in=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.UTF_8));
    String line;
    while((line=in.readLine())!=null) {
      try {
        String[] p=line.split("\t",2); String q=new String(Base64.getDecoder().decode(p[1]),StandardCharsets.UTF_8);
        if(p[0].equals("name") || p[0].equals("name_cml")) {
          OpsinResult r=NameToStructure.getInstance().parseChemicalName(q);
          System.out.println(r.getStatus()+"\t"+b(p[0].equals("name_cml") ? r.getCml() : r.getSmiles())+"\t"+b(r.getMessage())+"\t"+b(NameToStructure.getVersion()));
        } else {
          InchiOutput r=JnaInchi.molToInchi(q);
          System.out.println(r.getStatus()+"\t"+b(r.getInchi())+"\t"+b(r.getMessage())+"\t"+b(JnaInchi.inchiToInchiKey(r.getInchi()).getInchiKey())+"\t"+b(JnaInchi.getInchiLibraryVersion()));
        }
      } catch(Throwable e) {System.out.println("ERROR\t\t"+b(e.toString()));}
      System.out.flush();
    }
  }
}
