import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Base64;
import uk.ac.cam.ch.wwmm.opsin.*;
public class VersionProbe {
 static String b(String s){return Base64.getEncoder().encodeToString((s==null?"":s).getBytes(StandardCharsets.UTF_8));}
 static String warnings(OpsinResult p){StringBuilder s=new StringBuilder();for(OpsinWarning w:p.getWarnings())s.append(w.getType()).append(':').append(w.getMessage()).append('\n');return s.toString();}
 public static void main(String[] args)throws Exception{
  BufferedReader r=new BufferedReader(new InputStreamReader(System.in,StandardCharsets.UTF_8));String line;
  while((line=r.readLine())!=null){try{
   String name=new String(Base64.getDecoder().decode(line),StandardCharsets.UTF_8);
   OpsinResult p=NameToStructure.getInstance().parseChemicalName(name);
   System.out.println(b(NameToStructure.getVersion())+"\t"+b(p.getStatus().toString())+"\t"+b(p.getMessage())+"\t"+b(warnings(p))+"\t"+b(Boolean.toString(p.nameAppearsToBeAmbiguous()))+"\t"+b(p.getSmiles())+"\t"+b(p.getCml()));
  }catch(Throwable e){System.out.println("ERROR\t"+b(e.toString()));}System.out.flush();}
 }
}
