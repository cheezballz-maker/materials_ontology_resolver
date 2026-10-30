"""Readiness evidence is activity-specific; this module cannot mutate registry."""
import json
from pathlib import Path
H=Path(__file__).resolve().parent
def main():
 rows=[
 ('Chemical comparison','READY_WITHIN_VALIDATED_SCOPE','PARTIALLY_VALIDATED','PARTIALLY_VALIDATED','30/30 documentary graph labels; RW29 pending; advanced stereo/metal depiction outside validated exact scope.'),
 ('Source specificity','READY_WITHIN_VALIDATED_SCOPE','PARTIALLY_VALIDATED','PARTIALLY_VALIDATED','Incomplete, associated-name-only and broad referents remain unresolved; diagnostic source binding does not certify all future source adapters.'),
 ('Source reconciliation','READY_WITHIN_VALIDATED_SCOPE','PARTIALLY_VALIDATED','PARTIALLY_VALIDATED','Retained conflicts and new partial-stereo contradiction controls; no production migration.'),
 ('Candidate identification','READY_WITHIN_VALIDATED_SCOPE','PARTIALLY_VALIDATED','NOT_EVALUATED','Actual mode=ro full-key lookup: 31 inputs, 2 candidates. Absence is bounded retrieval only.'),
 ('Identity uniqueness','READY_WITHIN_VALIDATED_SCOPE','PARTIALLY_VALIDATED','NOT_EVALUATED','Retained duplicate/multiple and supported-plus-unresolved candidate controls; real lookup has only singleton hits.'),
 ('Evidence independence','PARTIALLY_VALIDATED','BLOCKED','BLOCKED','Auditable requirements and controlled tests; five real opportunities remain unestablished; two registry matches known dependent.'),
 ('Admission safety','READY_WITHIN_VALIDATED_SCOPE','PARTIALLY_VALIDATED','BLOCKED','Existing policy and qualification unchanged; all actual diagnostic admissions withheld. Synthetic positive/negative fixtures pass. Existing typed-source exemption and unknown-dependence qualification documented.'),
 ('Scientific validation','PARTIALLY_VALIDATED','PARTIALLY_VALIDATED','PARTIALLY_VALIDATED','Purposive documentary benchmark, not representative/blind/expert-reviewed; NIST fields contradict; qualified review pending.'),
 ('Registry integrity','READY_WITHIN_VALIDATED_SCOPE','NOT_EVALUATED','NOT_EVALUATED','Read-only SQLite checks plus protected hashes; ID reuse transactions/new creation deliberately not implemented or tested.')]
 result=dict(requirements=[dict(requirement=n,read_only_matching=a,existing_id_reuse=b,new_id_creation=c,evidence=e) for n,a,b,c,e in rows],recommendation='PROCEED_TO_READ_ONLY_REGISTRY_MATCHING',recommended_scope='Diagnostic proposals with qualified source binding, separate per-dimension evidence and no identity mutation/admission; keep unresolved forms and reference contradictions visible.',not_authorized_by_readiness=['Production ID reuse','Creation of new Substance IDs'],next_requirements_for_reuse=['Trace actual depositor/curator graph ancestry and validate at least one genuine positive corroboration path under unchanged provider policy','Independent chemical review of priority reference issues and expanded external corpus','Review existing typed-source and unknown-dependence policy semantics before promoting a diagnostic support result into admission'])
 (H/'evaluation/readiness_assessment.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
if __name__=='__main__':main()
