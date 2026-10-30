package uk.ac.cam.ch.wwmm.opsin;
import java.util.*;
public class Runner {
 static String warnings(OpsinResult r){StringBuilder s=new StringBuilder();for(OpsinWarning w:r.getWarnings())s.append(w.getType()).append(": ").append(w.getMessage()).append("\n");return s.toString();}
 static String b(String s){return s==null?"":Base64.getEncoder().encodeToString(s.getBytes(java.nio.charset.StandardCharsets.UTF_8));}
 public static void main(String[] args){
  boolean trace=Boolean.getBoolean("probe.trace");
  NameToStructure n=NameToStructure.getInstance();
  for(String s:args){if(trace)TraceProbe.reset(s);OpsinResult r=n.parseChemicalName(s);
   System.out.println("R\t"+b(s)+"\t"+r.getStatus()+"\t"+b(r.getMessage())+"\t"+b(r.getSmiles())+"\t"+b(r.getCml())+"\t"+b(warnings(r))+"\t"+r.nameAppearsToBeAmbiguous());
   if(trace)TraceProbe.dump(r);
  }
 }
}
