"""Reproduce initial interface outputs from its exact recorded source digest."""
import hashlib,json
from pathlib import Path
import bootstrap
H=Path(__file__).resolve().parent
def main():
 source=(H/'correspondence_assessment.py').read_text(encoding='utf8')
 comment=" # A selected molecular file can be compared even when another derived field\n # in its record disagrees. Keep that inconsistency in the full source-identity\n # assessment; do not let it conceal what the supplied graph itself represents.\n"
 assert source.count(comment)==1;source=source.replace(comment,'')
 old="ref=CanonicalCandidate(candidate.candidate_substance_id,candidate.preferred_name,candidate.structure,{**candidate.provenance,'identifiers':[]},"
 assert source.count(old)==1;source=source.replace(old,"ref=CanonicalCandidate(candidate.candidate_substance_id,candidate.preferred_name,candidate.structure,candidate.provenance,")
 extra=" rep['source_record_obligations']=source['obligations'];rep['candidate_record_obligations']=target['obligations'];rep['selected_reference_graph_scope_excludes_derived_identifier_assertions']=True\n"
 assert source.count(extra)==1;source=source.replace(extra,'')
 expected=json.loads((H/'evaluation/implementation_freeze_before_identifier_scope.json').read_text())['files']['correspondence_assessment.py'];assert hashlib.sha256(source.encode()).hexdigest()==expected,'INITIAL_INTERFACE_RECONSTRUCTION_HASH_MISMATCH'
 namespace={'__file__':str(H/'correspondence_assessment.py'),'__name__':'initial_scope_reproduction'};exec(compile(source,str(H/'correspondence_assessment.py'),'exec'),namespace)
 import validation_runner as runner
 code=(H/'validation_runner.py').read_text();needle="(H/f'evaluation/{partition}_results.json')";assert code.count(needle)==1;code=code.replace(needle,"(H/f'evaluation/{partition}_initial_results.json')")
 ctx={'__file__':str(H/'validation_runner.py'),'__name__':'initial_scope_runner'};exec(compile(code,str(H/'validation_runner.py'),'exec'),ctx);ctx['assess']=namespace['assess']
 for part in ('development_reference','frozen_evaluation'):ctx['main'](part)
 (H/'evaluation/initial_scope_reproduction.json').write_text(json.dumps({'source_sha256_verified':expected,'labels_changed':False,'output_method':'Recomputed exact initial interface; initial files were not backed up before final replay.','outputs':['development_reference_initial_results.json','frozen_evaluation_initial_results.json']},indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
