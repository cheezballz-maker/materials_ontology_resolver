"""Compile unmodified and diagnostic OPSIN core from the same frozen source."""
import difflib,hashlib,json,shutil,subprocess,sys,zipfile
from pathlib import Path

H=Path(__file__).resolve().parent;ROOT=H.parent.parent
SRC=H/'source_snapshot';JAVA=SRC/'opsin-core/src/main/java';RES=SRC/'opsin-core/src/main/resources'
JAR=ROOT/'opsin-master/opsin-cli/target/opsin-cli-3.0-SNAPSHOT-jar-with-dependencies.jar'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((H/'SOURCE_SNAPSHOT.json').read_text())
for name,want in manifest['files'].items():assert sha(SRC/name)==want,name
assert sha(JAR)==manifest['installed_jar_sha256']
diag=H/'diagnostic_source';assert not diag.exists();shutil.copytree(JAVA,diag)
package=diag/'uk/ac/cam/ch/wwmm/opsin';shutil.copy2(H/'OwnershipTrace.java',package/'OwnershipTrace.java')
namefile=package/'NameToStructure.java';stereofile=package/'StereochemistryHandler.java'
original={p.name:p.read_text(encoding='utf-8') for p in (namefile,stereofile)}
s=original[namefile.name]
def once(text,old,new):
    assert text.count(old)==1,old
    return text.replace(old,new)
s=once(s,'\t\tList<Element> parses;','\t\tOwnershipTrace.startCall();\n\t\tList<Element> parses;')
s=once(s,'\t\tfor(Element parse : parses) {','\t\tfor(Element parse : parses) {\n            OwnershipTrace.beginAttempt();')
s=once(s,'\t\t\t\t\treturn new OpsinResult(frag, OPSIN_RESULT_STATUS.SUCCESS, "", name);','\t\t\t\t\tOpsinResult selectedResult = new OpsinResult(frag, OPSIN_RESULT_STATUS.SUCCESS, "", name);\n\t\t\t\t\tOwnershipTrace.commitSuccess();\n\t\t\t\t\treturn selectedResult;')
namefile.write_text(s,encoding='utf-8')
s=original[stereofile.name]
marker='\tprivate void assignStereoCentre(Element stereoChemistryEl) throws StructureBuildingException, StereochemistryException {'
methods='''\tprivate String diagnosticPrior() {
        ArrayList<Integer> ids = new ArrayList<>();
        for (Atom a : atomStereoCentreMap.keySet())
            if (!notExplicitlyDefinedStereoCentreMap.containsKey(a)) ids.add(a.getID());
        Collections.sort(ids); return ids.toString();
    }
    private void diagnosticRecord(String kind, Element node, Fragment f, String locant, String path, String prior) {
        Atom a = f == null || locant == null ? null : f.getAtomByLocant(locant);
        OwnershipTrace.record(kind,node,node.getParent(),f,locant,a,
            a != null && atomStereoCentreMap.containsKey(a),
            a != null && notExplicitlyDefinedStereoCentreMap.containsKey(a),path,prior);
    }
'''
s=once(s,marker,methods+marker)
marker='\t\tStereoGroupType grpType = grpStr != null ? StereoGroupType.valueOf(grpStr) : StereoGroupType.Unk;\n\t\tfor (Fragment fragment : possibleFragments) {'
addition='''\t\tStereoGroupType grpType = grpStr != null ? StereoGroupType.valueOf(grpStr) : StereoGroupType.Unk;
        String tracePrior = diagnosticPrior();
        diagnosticRecord("DESCRIPTOR",stereoChemistryEl,null,locant,"",tracePrior);
        for (Fragment f : possibleFragments) diagnosticRecord("CANDIDATE",stereoChemistryEl,f,locant,"PRIMARY",tracePrior);
        Element diagnosticWord = parentSubBracketOrRoot.getParent();
        if (diagnosticWord.getName().equals(WORD_EL) && diagnosticWord.getChild(0).equals(parentSubBracketOrRoot)) {
            for (Element word : OpsinTools.getNextSiblingsOfType(diagnosticWord, WORD_EL))
                for (Element group : OpsinTools.getDescendantElementsWithTagName(word, GROUP_EL))
                    diagnosticRecord("CANDIDATE",stereoChemistryEl,group.getFrag(),locant,"FALLBACK",tracePrior);
        }
\t\tfor (Fragment fragment : possibleFragments) {'''
s=once(s,marker,addition)
marker='if (attemptAssignmentOfStereoCentreToFragment(fragment, rOrS, locant, grpType)) {\n\t\t\t\treturn;'
s=once(s,marker,'if (attemptAssignmentOfStereoCentreToFragment(fragment, rOrS, locant, grpType)) {\n                diagnosticRecord("SELECT",stereoChemistryEl,fragment,locant,"PRIMARY",tracePrior);\n\t\t\t\treturn;')
marker='if (attemptAssignmentOfStereoCentreToFragment(possibleGroups.get(i).getFrag(), rOrS, locant, grpType)) {\n\t\t\t\t\t\treturn;'
s=once(s,marker,'if (attemptAssignmentOfStereoCentreToFragment(possibleGroups.get(i).getFrag(), rOrS, locant, grpType)) {\n                        diagnosticRecord("SELECT",stereoChemistryEl,possibleGroups.get(i).getFrag(),locant,"FALLBACK",tracePrior);\n\t\t\t\t\t\treturn;')
stereofile.write_text(s,encoding='utf-8')
patch=[]
for p in (namefile,stereofile):patch.extend(difflib.unified_diff(original[p.name].splitlines(True),p.read_text(encoding='utf-8').splitlines(True),fromfile='baseline/'+p.name,tofile='diagnostic/'+p.name))
(H/'diagnostic.patch').write_text(''.join(patch),encoding='utf-8')

def compile_tree(label,tree):
    out=H/(label+'_classes');out.mkdir()
    files=sorted(tree.rglob('*.java'))
    args=H/(label+'_javac.args')
    # javac argument file uses quoted absolute paths on Windows.
    args.write_text('\n'.join('"'+str(p.resolve()).replace('\\','/')+'"' for p in files),encoding='utf-8')
    cmd=['javac','--release','8','-encoding','UTF-8','-cp',str(JAR),'-d',str(out),'@'+str(args)]
    result=subprocess.run(cmd,capture_output=True,text=True,encoding='utf-8',errors='replace')
    (H/(label+'_build.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
    if result.returncode:raise RuntimeError(label+' build failed; see build log')
    shutil.copytree(RES,out,dirs_exist_ok=True)
    props=out/'uk/ac/cam/ch/wwmm/opsin/opsinbuild.props'
    props.write_text(props.read_text(encoding='utf-8').replace('${project.version}','3.0-SNAPSHOT'),encoding='utf-8')
    archive=H/(label+'_core.jar')
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for p in sorted(x for x in out.rglob('*') if x.is_file()):
            zi=zipfile.ZipInfo(p.relative_to(out).as_posix(),(2020,1,1,0,0,0));zi.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(zi,p.read_bytes())
    return out,archive,len(files)

baseline,bjar,n=compile_tree('baseline',JAVA)
diagnostic,djar,dn=compile_tree('diagnostic',diag)
def classes(p):return {x.relative_to(p).as_posix():sha(x) for x in p.rglob('*.class')}
bc,dc=classes(baseline),classes(diagnostic)
changed=sorted(k for k in bc if bc[k]!=dc.get(k));added=sorted(set(dc)-set(bc));removed=sorted(set(bc)-set(dc))
allowed={'uk/ac/cam/ch/wwmm/opsin/NameToStructure.class','uk/ac/cam/ch/wwmm/opsin/StereochemistryHandler.class'}
assert set(changed)<=allowed and set(added)=={'uk/ac/cam/ch/wwmm/opsin/OwnershipTrace.class'} and not removed,(changed,added,removed)
out=dict(source_manifest_sha256=manifest['source_tree_manifest_sha256'],source_revision=manifest['revision'],source_java_files=n,diagnostic_java_files=dn,
    baseline_jar_sha256=sha(bjar),diagnostic_jar_sha256=sha(djar),dependency_jar_sha256=sha(JAR),changed_classes=changed,added_classes=added,removed_classes=removed,
    patch_sha256=sha(H/'diagnostic.patch'),helper_sha256=sha(H/'OwnershipTrace.java'),compiler=subprocess.check_output(['javac','-version'],text=True,stderr=subprocess.STDOUT).strip(),
    config='javac --release 8 -encoding UTF-8; source resources; Maven-filtered project.version=3.0-SNAPSHOT; installed shaded jar for dependencies')
(H/'BUILD_IDENTITY.json').write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out,indent=2))
