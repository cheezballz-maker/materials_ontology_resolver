"""Rebuild in a new directory from a clean pinned OPSIN checkout; no admission code."""
import argparse,subprocess,shutil,hashlib,json
from pathlib import Path
PIN='b91b610af5ab07560fedb20730d7aef46bb2bca0'
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();a.source=a.source.resolve();a.out=a.out.resolve()
B=Path(__file__).resolve().parent
assert subprocess.check_output(['git','-C',str(a.source),'rev-parse','HEAD'],text=True).strip()==PIN
assert not subprocess.check_output(['git','-C',str(a.source),'status','--porcelain'],text=True).strip(),'Use clean pinned checkout'
a.out.mkdir(parents=True,exist_ok=False)
shutil.copytree(a.source,a.out/'source',ignore=shutil.ignore_patterns('.git','target'))
shutil.copytree(a.out/'source/opsin-core/src',a.out/'instrumented/src')
for f in B.glob('*.jar'):shutil.copy2(f,a.out/f.name)
for f in ['Runner.java','run_probes.py','test_trace.py','diagnostic.patch']:shutil.copy2(B/f,a.out/f)
for f in (a.out/'instrumented/src/main/java').rglob('*.java'):f.write_text(f.read_text())
subprocess.run(['patch','-p1'],cwd=a.out/'instrumented',input=(B/'diagnostic.patch').read_text().replace('a/opsin-core/','a/').replace('b/opsin-core/','b/'),text=True,check=True,stdout=subprocess.DEVNULL)
def compile(src,out,extra=(),cp='opsin-core-2.9.0.jar'):
 files=[str(f.relative_to(a.out)) for f in (a.out/src).rglob('*.java')]+list(extra)
 (a.out/out).mkdir()
 subprocess.run(['java','com.sun.tools.javac.Main','--release','8','-encoding','UTF-8','-cp',cp,'-d',out,*files],cwd=a.out,check=True)
jar=a.out/'opsin-core-2.9.0.jar';assert hashlib.sha256(jar.read_bytes()).hexdigest()=='627ee5da4af551f9c4d1d766f545eb7cf519a344776e0bb677247a47abac0252'
compile('source/opsin-core/src/main/java','baseline-classes')
compile('instrumented/src/main/java','diagnostic-classes',['Runner.java'])
r=a.out/'runner-classes/uk/ac/cam/ch/wwmm/opsin';r.mkdir(parents=True)
for f in (a.out/'diagnostic-classes/uk/ac/cam/ch/wwmm/opsin').glob('TraceProbe*.class'):shutil.copy2(f,r/f.name)
shutil.copy2(a.out/'diagnostic-classes/uk/ac/cam/ch/wwmm/opsin/Runner.class',r/'Runner.class')
with (a.out/'probe_summary.json').open('w') as log:subprocess.run(['python','run_probes.py'],cwd=a.out,check=True,stdout=log)
with (a.out/'trace-tests.log').open('w') as log:subprocess.run(['python','test_trace.py'],cwd=a.out,check=True,stdout=log,stderr=subprocess.STDOUT)
compile('source/opsin-core/src/test/java','test-classes',cp='baseline-classes:opsin-core-2.9.0.jar:junit-console.jar:hamcrest.jar:mockito.jar')
for mode in ['baseline','diagnostic']:
 cp=[mode+'-classes','test-classes','source/opsin-core/src/main/resources','source/opsin-core/src/test/resources','opsin-core-2.9.0.jar','hamcrest.jar','mockito.jar','byte-buddy.jar','byte-buddy-agent.jar','objenesis.jar']
 with (a.out/f'junit-{mode}.log').open('w') as log:subprocess.run(['java','-jar','junit-console.jar','execute','--class-path',':'.join(cp),'--scan-class-path','--details','summary','--reports-dir','junit-'+mode],cwd=a.out,check=True,stdout=log,stderr=subprocess.STDOUT)
print(json.dumps({'out':str(a.out),'result':'all probe and core test commands passed'}))
