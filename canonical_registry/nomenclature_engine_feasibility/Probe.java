import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import uk.ac.cam.ch.wwmm.opsin.*;
public class Probe {
  static String b(String s) { return Base64.getEncoder().encodeToString((s==null?"":s).getBytes(StandardCharsets.UTF_8)); }
  public static void main(String[] args) throws Exception {
    BufferedReader in=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.UTF_8));
    String line;
    while((line=in.readLine())!=null){
      try {
        String n=new String(Base64.getDecoder().decode(line),StandardCharsets.UTF_8);
        OpsinResult r=NameToStructure.getInstance().parseChemicalName(n);
        String std="",fixed="";
        if(r.getStatus()!=OpsinResult.OPSIN_RESULT_STATUS.FAILURE){
          std=NameToInchi.convertResultToStdInChI(r);fixed=NameToInchi.convertResultToInChI(r);
        }
        System.out.println(b(NameToStructure.getVersion())+"\t"+b(r.getStatus().toString())+"\t"+b(r.getMessage())+"\t"+b(r.getWarnings().toString())+"\t"+b(Boolean.toString(r.nameAppearsToBeAmbiguous()))+"\t"+b(Boolean.toString(r.stereochemistryIgnored()))+"\t"+b(r.getSmiles())+"\t"+b(r.getExtendedSmiles())+"\t"+b(r.getCml())+"\t"+b(std)+"\t"+b(fixed));
      } catch(Throwable ex) {System.out.println("ERROR\t"+b(ex.toString()));}
      System.out.flush();
    }
  }
}
