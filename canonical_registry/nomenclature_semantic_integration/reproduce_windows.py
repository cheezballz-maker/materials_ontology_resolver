"""Reproduce bundle's baseline and instrumented controls in a disposable short path."""
import hashlib,json,os,shutil,subprocess,tempfile
from pathlib import Path
H=Path(__file__).resolve().parent;P=H/'poc_bundle';src=H/'opsin-2.9.0'
pin='b91b610af5ab07560fedb20730d7aef46bb2bca0'
assert subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()==pin
assert not subprocess.check_output(['git','-c','core.longpaths=true','-C',str(src),'status','--porcelain'],text=True).strip()
out=Path(tempfile.mkdtemp(prefix='opsin-h-'));print('Disposable build:',out,flush=True)
shutil.copytree(src,out/'source',ignore=shutil.ignore_patterns('.git','target'))
shutil.copytree(out/'source',out/'instrumented')
for f in (out/'instrumented/opsin-core/src/main/java').rglob('*.java'):
 f.write_text(f.read_text(encoding='utf8').replace('\r\n','\n'),encoding='utf8',newline='\n')
subprocess.run(['git','apply','--ignore-whitespace',str(P/'diagnostic.patch')],cwd=out/'instrumented',check=True)
for f in P.glob('*.jar'):shutil.copy2(f,out/f.name)
shutil.copy2(P/'test_trace.py',out/'test_trace.py')
runner_source=(P/'Runner.java').read_text(encoding='utf8').replace('for(String s:args){','for(String encoded:args){String s=new String(Base64.getDecoder().decode(encoded),java.nio.charset.StandardCharsets.UTF_8);')
(out/'Runner.java').write_text(runner_source,encoding='utf8')
rp=(P/'run_probes.py').read_text(encoding='utf8').replace("':'.join(map(str,cp))","__import__('os').pathsep.join(map(str,cp))").replace('*names]', '*[base64.b64encode(n.encode()).decode() for n in names]]')
(out/'run_probes.py').write_text(rp,encoding='utf8')
jar=out/'opsin-core-2.9.0.jar';assert hashlib.sha256(jar.read_bytes()).hexdigest()=='627ee5da4af551f9c4d1d766f545eb7cf519a344776e0bb677247a47abac0252'
def compile(folder,dest,extra=(),classpath='opsin-core-2.9.0.jar'):
 files=[str(f.relative_to(out)) for f in (out/folder).rglob('*.java')]+list(extra)
 (out/dest).mkdir()
 subprocess.run(['javac','--release','8','-encoding','UTF-8','-cp',classpath,'-d',dest,*files],cwd=out,check=True)
compile('source/opsin-core/src/main/java','baseline-classes')
compile('instrumented/opsin-core/src/main/java','diagnostic-classes',['Runner.java'])
runner=out/'runner-classes/uk/ac/cam/ch/wwmm/opsin';runner.mkdir(parents=True)
for f in (out/'diagnostic-classes/uk/ac/cam/ch/wwmm/opsin').glob('TraceProbe*.class'):shutil.copy2(f,runner/f.name)
shutil.copy2(out/'diagnostic-classes/uk/ac/cam/ch/wwmm/opsin/Runner.class',runner/'Runner.class')
env=dict(os.environ,PYTHONUTF8='1')
for name,script in [('probe_summary.json','run_probes.py'),('trace-tests.log','test_trace.py')]:
 with (out/name).open('w',encoding='utf8') as log:subprocess.run([os.sys.executable,script],cwd=out,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
compile('source/opsin-core/src/test/java','test-classes',classpath=os.pathsep.join(['baseline-classes','opsin-core-2.9.0.jar','junit-console.jar','hamcrest.jar','mockito.jar']))
for mode in ('baseline','diagnostic'):
 cp=[mode+'-classes','test-classes','source/opsin-core/src/main/resources','source/opsin-core/src/test/resources','opsin-core-2.9.0.jar','hamcrest.jar','mockito.jar','byte-buddy.jar','byte-buddy-agent.jar','objenesis.jar']
 with (out/f'junit-{mode}.log').open('w',encoding='utf8') as log:subprocess.run(['java','-jar','junit-console.jar','execute','--class-path',os.pathsep.join(cp),'--scan-class-path','--details','summary'],cwd=out,stdout=log,stderr=subprocess.STDOUT,check=True)
for n in ('probe_summary.json','probe_results.json','trace-tests.log','junit-baseline.log','junit-diagnostic.log','trace.tsv','trace.stderr'):
 shutil.copy2(out/n,H/('reproduced-'+n))
(H/'reproduction_manifest.json').write_text(json.dumps({'status':'PASS','temp_build':str(out),'pin':pin,'adaptation':'classpath separator and base64 argument transport adapted for Windows; instrumentation patch unchanged'},indent=2),encoding='utf8')
print('PASS: public equivalence, trace controls, baseline and diagnostic core suites',flush=True)
