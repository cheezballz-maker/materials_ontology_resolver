"""Instrument locanted substitution in a disposable OPSIN source copy."""
import base64,difflib,hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
base=Path(json.loads((B/'operation_semantic_poc/build_manifest.json').read_text())['temporary_build'])
out=Path(tempfile.mkdtemp(prefix='opsin-sub-'));print('Build',out,flush=True)
shutil.copytree(base/'instrumented',out/'instrumented');shutil.copytree(base/'source',out/'source');shutil.copytree(base/'baseline-classes',out/'baseline-classes');shutil.copytree(base/'test-classes',out/'test-classes')
for n in ('opsin-core-2.9.0.jar','junit-console.jar','hamcrest.jar','mockito.jar','byte-buddy.jar','byte-buddy-agent.jar','objenesis.jar','Runner.java'):shutil.copy2(base/n,out/n)
root=out/'instrumented/opsin-core/src/main/java/uk/ac/cam/ch/wwmm/opsin';diff=[]
def change(name,items):
 p=root/name;old=p.read_text(encoding='utf8');new=old
 for a,b in items:
  assert new.count(a)==1,(name,a[:80],new.count(a));new=new.replace(a,b,1)
 p.write_text(new,encoding='utf8',newline='\n');diff.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+name,tofile='b/'+name))
change('ComponentProcessor.java',[
 ('subOrBracket.addAttribute(new Attribute(LOCANT_ATR, locantEl.getValue()));\n\t\t\tlocantEl.detach();','subOrBracket.addAttribute(new Attribute(LOCANT_ATR, locantEl.getValue()));\n\t\t\tTraceProbe.copy(locantEl,subOrBracket);\n\t\t\tlocantEl.detach();')])
change('StructureBuildingMethods.java',[
 ('\t\t\t\t\tjoinFragmentsSubstitutively(state, frag, atomToSubstituteAt);\n\t\t\t\t}', '\t\t\t\t\tAtom traceAttachment=frag.getOutAtom(0).getAtom();\n\t\t\t\t\tjoinFragmentsSubstitutively(state, frag, atomToSubstituteAt);\n\t\t\t\t\tTraceProbe.substitution(subBracketOrRoot,group,parentFrag,atomToSubstituteAt,traceAttachment,locantString);\n\t\t\t\t}')])
change('TraceProbe.java',[
 ('static List<Mutation> mutations;', '''static List<Mutation> mutations;
 static List<Substitution> substitutions;
 static class Substitution {Element node,group;Origin loc,sub;Fragment parent;Atom target,attachment;String locant,sourceNodes;int order;boolean bonded;
  Substitution(Element n,Element g,Fragment f,Atom t,Atom a,String l){node=n;group=g;parent=f;target=t;attachment=a;locant=l;loc=origins.get(n);sub=origins.get(g);sourceNodes=sourceDescendants(n);order=mutations.size();bonded=t.getBondToAtom(a)!=null;}}
 static String sourceDescendants(Element n){StringBuilder s=new StringBuilder();appendSources(n,s);return s.toString();}
 static void appendSources(Element n,StringBuilder s){Origin o=origins.get(n);if(o!=null)s.append(o.start).append(':').append(o.end).append(':').append(o.text).append(';');for(Element x:n.getChildElements())appendSources(x,s);}
 static void substitution(Element n,Element g,Fragment f,Atom t,Atom a,String l){if(substitutions!=null)substitutions.add(new Substitution(n,g,f,t,a,l));}'''),
 ('events=new ArrayList<>();mutations=new ArrayList<>();','events=new ArrayList<>();mutations=new ArrayList<>();substitutions=new ArrayList<>();'),
 ('events.clear();mutations.clear();selected=false;cloned=false;','events.clear();mutations.clear();substitutions.clear();selected=false;cloned=false;'),
 ('  for(Mutation m:mutations){boolean relevant=false;', '''  for(Substitution s:substitutions){boolean sameH=false;for(Event e:events)if(e.a==s.target)sameH=true;
   boolean targetFinal=r.getStructure().getAtomList().contains(s.target),attachmentFinal=r.getStructure().getAtomList().contains(s.attachment);
   System.out.println("S\\t"+(s.loc==null?-1:s.loc.start)+"\\t"+(s.loc==null?-1:s.loc.end)+"\\t"+b64(s.loc==null?null:s.loc.text)+"\\t"+(s.sub==null?-1:s.sub.start)+"\\t"+(s.sub==null?-1:s.sub.end)+"\\t"+b64(s.sub==null?null:s.sub.text)+"\\t"+b64(s.sourceNodes)+"\\t"+b64(s.node.toXML())+"\\t"+b64(s.group.getValue())+"\\t"+b64(s.locant)+"\\t"+s.target.getID()+"\\t"+s.attachment.getID()+"\\t"+s.bonded+"\\t"+sameH+"\\t"+targetFinal+"\\t"+attachmentFinal+"\\t"+cloned+"\\t"+s.order+"\\t"+attempts);
  }
  for(Mutation m:mutations){boolean relevant=false;''')])
(H/'substitution-instrumentation.patch').write_text(''.join(diff),encoding='utf8')
classes=out/'substitution-classes';classes.mkdir();files=[str(p) for p in root.rglob('*.java')]+[str(out/'Runner.java')]
subprocess.run(['javac','--release','8','-encoding','UTF-8','-cp',str(out/'opsin-core-2.9.0.jar'),'-d',str(classes),*files],check=True)
controls=json.loads((H/'frozen_controls.json').read_text(encoding='utf8'));names=list(dict.fromkeys(x[k] for x in controls['development'] for k in ('source','candidate') if x[k]!='same-source'))
encoded=[base64.b64encode(n.encode('utf8')).decode('ascii') for n in names]
def run(label,mode):
 cp=([str(classes)] if mode else [str(out/'baseline-classes'),str(classes)])+[str(out/'source/opsin-core/src/main/resources'),str(out/'opsin-core-2.9.0.jar')]
 p=subprocess.run(['java','-Dprobe.trace='+str(mode).lower(),'-cp',os.pathsep.join(cp),'uk.ac.cam.ch.wwmm.opsin.Runner',*encoded],capture_output=True,text=True,encoding='utf8',timeout=120,check=True)
 (H/f'{label}.tsv').write_text(p.stdout,encoding='utf8');(H/f'{label}.stderr').write_text(p.stderr,encoding='utf8')
run('development_trace',True);run('development_baseline',False)
runner=out/'runner-classes/uk/ac/cam/ch/wwmm/opsin';runner.mkdir(parents=True)
for f in (classes/'uk/ac/cam/ch/wwmm/opsin').glob('TraceProbe*.class'):shutil.copy2(f,runner/f.name)
shutil.copy2(classes/'uk/ac/cam/ch/wwmm/opsin/Runner.class',runner/'Runner.class')
probe=(base/'run_probes.py').read_text(encoding='utf8').replace("('operation' if mode=='trace' else 'baseline')","('substitution' if mode=='trace' else 'baseline')")
(out/'run_probes.py').write_text(probe,encoding='utf8');shutil.copy2(base/'test_trace.py',out/'test_trace.py')
env=dict(os.environ,PYTHONUTF8='1')
for label,script in [('prior-probe-summary.log','run_probes.py'),('indicated-h-tests.log','test_trace.py')]:
 with (H/label).open('w',encoding='utf8') as log:subprocess.run([os.sys.executable,script],cwd=out,stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
for mode in ('baseline','substitution'):
 cp=[mode+'-classes','test-classes','source/opsin-core/src/main/resources','source/opsin-core/src/test/resources','opsin-core-2.9.0.jar','hamcrest.jar','mockito.jar','byte-buddy.jar','byte-buddy-agent.jar','objenesis.jar']
 with (H/f'junit-{mode}.log').open('w',encoding='utf8') as log:subprocess.run(['java','-jar','junit-console.jar','execute','--class-path',os.pathsep.join(cp),'--scan-class-path','--details','summary'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
(H/'build.json').write_text(json.dumps({'status':'PASS','temp_build':str(out),'upstream':'b91b610af5ab07560fedb20730d7aef46bb2bca0','development_names':len(names),'holdout_run':False,'patch_sha256':hashlib.sha256((H/'substitution-instrumentation.patch').read_bytes()).hexdigest()},indent=2),encoding='utf8')
print('PASS isolated build and core suites',flush=True)
