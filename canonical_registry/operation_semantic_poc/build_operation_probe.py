"""Isolated observable-mutation probe atop the previously reproduced OPSIN POC.

Observations are not claimed to be a complete semantic operation lineage.
"""
import difflib,json,os,shutil,subprocess,tempfile
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;prior=B/'nomenclature_semantic_integration'
base=Path(json.loads((prior/'reproduction_manifest.json').read_text())['temp_build'])
out=Path(tempfile.mkdtemp(prefix='opsin-op-'));print('Build',out,flush=True)
shutil.copytree(base/'instrumented',out/'instrumented')
for n in ('opsin-core-2.9.0.jar','junit-console.jar','hamcrest.jar','mockito.jar','byte-buddy.jar','byte-buddy-agent.jar','objenesis.jar','Runner.java','run_probes.py','test_trace.py'):shutil.copy2(base/n,out/n)
shutil.copytree(base/'source',out/'source');shutil.copytree(base/'baseline-classes',out/'baseline-classes');shutil.copytree(base/'test-classes',out/'test-classes')
root=out/'instrumented/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin';diff=[]
def change(name,replacements):
 p=root/name;old=p.read_text(encoding='utf8');new=old
 for a,b in replacements:
  assert new.count(a)==1,(name,a[:100],new.count(a));new=new.replace(a,b,1)
 p.write_text(new,encoding='utf8',newline='\n');diff.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
change('TraceProbe.java',[
 ('Atom a; boolean spare; int fragment;', 'Atom a; boolean spare; int fragment,operationCursor; String parentState;'),
 ('spare=atom.hasSpareValency();fragment=System.identityHashCode(f);', 'spare=atom.hasSpareValency();fragment=System.identityHashCode(f);operationCursor=mutations.size();parentState=snapshot(atom);'),
 ('+"\\t"+e.fragment);', '+"\\t"+e.fragment+"\\t"+e.operationCursor+"\\t"+b64(e.parentState));'),
 ('static List<Event> events;', '''static List<Event> events;
 static class Mutation {int seq; String type,preA,postA,preB,postB; Atom a,b; Mutation(String t,Atom x,Atom y,String pa,String pb){seq=mutations.size();type=t;a=x;b=y;preA=pa;preB=pb;postA=snapshot(x);postB=snapshot(y);}}
 static List<Mutation> mutations;
 static String snapshot(Atom a){if(a==null)return "";return a.getElement()+":"+a.getCharge()+":"+a.getProtonsExplicitlyAddedOrRemoved()+":"+a.hasSpareValency()+":"+a.getIncomingValency()+":"+a.getBonds().size();}
 static void mutation(String type,Atom a,Atom b,String preA,String preB){if(mutations!=null)mutations.add(new Mutation(type,a,b,preA,preB));}'''),
 ('events=new ArrayList<>();}','events=new ArrayList<>();mutations=new ArrayList<>();}'),
 ('events.clear();selected=false;cloned=false;','events.clear();mutations.clear();selected=false;cloned=false;'),
 ('  for(Event e:events){Origin o=e.o;', '''  for(Mutation m:mutations){boolean relevant=false;for(Event e:events)if(e.a==m.a || e.a==m.b)relevant=true;
   if(relevant)System.out.println("O\\t"+m.seq+"\\t"+m.type+"\\t"+(m.a==null?-1:m.a.getID())+"\\t"+(m.b==null?-1:m.b.getID())+"\\t"+b64(m.preA)+"\\t"+b64(m.postA)+"\\t"+b64(m.preB)+"\\t"+b64(m.postB)+"\\tSOURCE_NOT_CAPTURED");}
  for(Event e:events){Origin o=e.o;''')])
change('FragmentManager.java',[
 ('Bond createBond(Atom fromAtom, Atom toAtom, int bondOrder) {\n\t\tBond b =', 'Bond createBond(Atom fromAtom, Atom toAtom, int bondOrder) {\n\t\tString opA=TraceProbe.snapshot(fromAtom),opB=TraceProbe.snapshot(toAtom);\n\t\tBond b ='),
 ('\t\treturn b;\n\t}\n\t\n\tvoid removeAtomAndAssociatedBonds', '\t\tTraceProbe.mutation("BOND_CREATE_"+bondOrder,fromAtom,toAtom,opA,opB);\n\t\treturn b;\n\t}\n\t\n\tvoid removeAtomAndAssociatedBonds'),
 ('void removeBond(Bond bond){\n\t\tbond.getFromAtom()', 'void removeBond(Bond bond){\n\t\tAtom opFrom=bond.getFromAtom(),opTo=bond.getToAtom();String opA=TraceProbe.snapshot(opFrom),opB=TraceProbe.snapshot(opTo);\n\t\tbond.getFromAtom()'),
 ('\t\tremoveInterFragmentBondIfPresent(bond);\n\t}', '\t\tremoveInterFragmentBondIfPresent(bond);\n\t\tTraceProbe.mutation("BOND_REMOVE",opFrom,opTo,opA,opB);\n\t}')])
change('Bond.java',[
 ('void setOrder(int order) {\n\t\tthis.order = order;', 'void setOrder(int order) {\n\t\tString opA=TraceProbe.snapshot(from),opB=TraceProbe.snapshot(to);int oldOrder=this.order;\n\t\tthis.order = order;\n\t\tTraceProbe.mutation("BOND_ORDER_"+oldOrder+"_TO_"+order,from,to,opA,opB);'),
 ('void addOrder(int o) {\n\t\torder += o;', 'void addOrder(int o) {\n\t\tString opA=TraceProbe.snapshot(from),opB=TraceProbe.snapshot(to);int oldOrder=order;\n\t\torder += o;\n\t\tTraceProbe.mutation("BOND_ORDER_"+oldOrder+"_TO_"+order,from,to,opA,opB);')])
change('Atom.java',[
 ('void setElement(ChemEl chemEl) {\n\t\tthis.chemEl = chemEl;', 'void setElement(ChemEl chemEl) {\n\t\tString opA=TraceProbe.snapshot(this);\n\t\tthis.chemEl = chemEl;\n\t\tTraceProbe.mutation("ELEMENT_SET",this,null,opA,"");'),
 ('void addChargeAndProtons(int charge, int protons){\n\t\tthis.charge += charge;\n\t\tprotonsExplicitlyAddedOrRemoved+=protons;', 'void addChargeAndProtons(int charge, int protons){\n\t\tString opA=TraceProbe.snapshot(this);\n\t\tthis.charge += charge;\n\t\tprotonsExplicitlyAddedOrRemoved+=protons;\n\t\tTraceProbe.mutation("CHARGE_AND_PROTON_DELTA",this,null,opA,"");'),
 ('void setCharge(int c) {\n\t\tcharge = c;', 'void setCharge(int c) {\n\t\tString opA=TraceProbe.snapshot(this);\n\t\tcharge = c;\n\t\tTraceProbe.mutation("CHARGE_SET",this,null,opA,"");'),
 ('void setProtonsExplicitlyAddedOrRemoved(int protonsExplicitlyAddedOrRemoved) {\n\t\tthis.protonsExplicitlyAddedOrRemoved = protonsExplicitlyAddedOrRemoved;', 'void setProtonsExplicitlyAddedOrRemoved(int protonsExplicitlyAddedOrRemoved) {\n\t\tString opA=TraceProbe.snapshot(this);\n\t\tthis.protonsExplicitlyAddedOrRemoved = protonsExplicitlyAddedOrRemoved;\n\t\tTraceProbe.mutation("PROTON_COUNT_SET",this,null,opA,"");'),
 ('void setSpareValency(boolean sv) {\n\t\tspareValency = sv;', 'void setSpareValency(boolean sv) {\n\t\tString opA=TraceProbe.snapshot(this);\n\t\tspareValency = sv;\n\t\tTraceProbe.mutation("SPARE_VALENCY_SET",this,null,opA,"");')])
(H/'operation-instrumentation.patch').write_text(''.join(diff),encoding='utf8')
classes=out/'operation-classes';classes.mkdir();files=[str(p) for p in (out/'instrumented/opsin-core/src/main/java').rglob('*.java')]+[str(out/'Runner.java')]
subprocess.run(['javac','--release','8','-encoding','UTF-8','-cp',str(out/'opsin-core-2.9.0.jar'),'-d',str(classes),*files],check=True)
run=(out/'run_probes.py').read_text(encoding='utf8').replace("('diagnostic' if mode=='trace' else 'baseline')","('operation' if mode=='trace' else 'baseline')")
(out/'run_probes.py').write_text(run,encoding='utf8')
runner=out/'runner-classes/uk/ac/cam/ch/wwmm/opsin'
runner.mkdir(parents=True)
for f in (classes/'uk/ac/cam/ch/wwmm/opsin').glob('TraceProbe*.class'):shutil.copy2(f,runner/f.name)
shutil.copy2(classes/'uk/ac/cam/ch/wwmm/opsin/Runner.class',runner/'Runner.class')
env=dict(os.environ,PYTHONUTF8='1')
with (out/'probe_summary.log').open('w',encoding='utf8') as f:subprocess.run([os.sys.executable,'run_probes.py'],cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
with (out/'trace-tests.log').open('w',encoding='utf8') as f:subprocess.run([os.sys.executable,'test_trace.py'],cwd=out,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
for mode in ('baseline','operation'):
 cp=[mode+'-classes','test-classes','source/opsin-core/src/main/resources','source/opsin-core/src/test/resources','opsin-core-2.9.0.jar','hamcrest.jar','mockito.jar','byte-buddy.jar','byte-buddy-agent.jar','objenesis.jar']
 with (out/f'junit-{mode}.log').open('w',encoding='utf8') as f:subprocess.run(['java','-jar','junit-console.jar','execute','--class-path',os.pathsep.join(cp),'--scan-class-path','--details','summary'],cwd=out,stdout=f,stderr=subprocess.STDOUT,check=True)
for n in ('probe_results.json','probe_summary.log','baseline.tsv','released.tsv','trace.tsv','trace-tests.log','junit-baseline.log','junit-operation.log'):shutil.copy2(out/n,H/n)
(H/'build_manifest.json').write_text(json.dumps({'status':'PASS','temporary_build':str(out),'input':'prior reproduced POC with pinned 2.9.0','mutation_provenance':'NOT_CAPTURED','coverage':'OBSERVATIONAL_INCOMPLETE'},indent=2),encoding='utf8')
print('PASS: public outputs, trace controls and operation-instrumented core tests',flush=True)
