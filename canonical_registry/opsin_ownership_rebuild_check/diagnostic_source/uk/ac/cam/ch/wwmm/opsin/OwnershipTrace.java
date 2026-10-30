package uk.ac.cam.ch.wwmm.opsin;

import java.util.*;
import java.nio.charset.StandardCharsets;

/** Diagnostic only. Buffer events per parse; publish only a selected SUCCESS. */
final class OwnershipTrace {
    private static int attempt;
    private static List<String[]> events;
    private static IdentityHashMap<Object,Integer> ids;
    private static int nextId;
    static void startCall() { attempt=0; events=null; ids=null; }
    static void beginAttempt() { attempt++; events=new ArrayList<>(); ids=new IdentityHashMap<>(); nextId=1; }
    static int id(Object o) {
        if (o==null) return 0;
        Integer n=ids.get(o); if(n==null){n=nextId++;ids.put(o,n);} return n;
    }
    static String xml(Element e) {return e==null ? "" : e.toXML();}
    static String b(String s) {return Base64.getEncoder().encodeToString((s==null?"":s).getBytes(StandardCharsets.UTF_8));}
    static void record(String kind, Element node, Element scope, Fragment fragment, String locant, Atom atom,
                       boolean potential, boolean unassigned, String path, String priorIds) {
        if(events==null) return;
        String[] row={String.valueOf(attempt),kind,String.valueOf(id(node)),String.valueOf(id(scope)),
            xml(node),xml(scope),String.valueOf(id(fragment)),xml(fragment==null?null:fragment.getTokenEl()),
            locant==null?"":locant,atom==null?"":String.valueOf(atom.getID()),
            String.valueOf(potential),String.valueOf(unassigned),path,priorIds};
        events.add(row);
    }
    static void commitSuccess() {
        System.err.println("OWNERSHIP_BEGIN\t"+attempt);
        for(String[] row:events) {
            StringBuilder s=new StringBuilder("OWNERSHIP_EVENT");
            for(String v:row)s.append('\t').append(b(v));
            System.err.println(s.toString());
        }
        System.err.println("OWNERSHIP_SUCCESS\t"+attempt);
        events=null;
    }
}
