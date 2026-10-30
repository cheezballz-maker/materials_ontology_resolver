"""Describe frozen false holds before any nomenclature implementation."""
import collections,json,re
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
rows=[r for r in read(B/'deterministic_form_remediation/newly_blocked_cases.json') if r['prior_verdict']=='CORRECT']
assert len(rows)==81
out=[]
for r in rows:
    name=r['name'];s=name.lower();reasons=r['reasons'];claims=r['source_form']['claims']
    patterns=[]
    if re.search(r'(?<!\w)\d+[a-z]?h(?=[-,)])',s):patterns.append('indicated_hydrogen_token_requires_locant_mapping')
    if re.search(r'nitro',s):patterns.append('nitro_group_may_explain_internal_formal_charges')
    if re.search(r'acid|carboxyl|sulphon|sulfon',s):patterns.append('acid_or_acid_derivative_context')
    if re.search(r'amide|imide|carbam',s):patterns.append('amide_imide_or_carbamoyl_context')
    if re.search(r'one|oxo|acetyl|aldehyde|pentenal',s):patterns.append('carbonyl_or_oxo_context')
    if re.search(r'phenol|hydroxy|naphthol',s):patterns.append('hydroxy_context')
    if re.search(r'pyr|triaz|thiaz|quinol|indol|imidazol',s):patterns.append('heterocycle_context')
    if not patterns:patterns=['other_nomenclature_or_claim_scope']
    conflicts={c['alias']:c for c in r['source_form']['source_claim_conflicts']}
    aliases=[]
    for c in claims:
        if c['claim_type']!='alias':continue
        comparison=c.get('candidate_comparison','NOT_COMPARED');conflict=conflicts.get(c['text'])
        strength=('UNPARSEABLE_ALIAS' if c['parsed_interpretation']['status']!='SUCCESS' else
                  'PARSED_EQUIVALENT_SCOPE_UNVERIFIED' if comparison=='EXACT' else
                  'PARSER_SPECIFIC_INCOMPATIBLE_SCOPE_UNVERIFIED' if conflict and conflict['alias_specific'] else
                  'PARSER_BROAD_OR_UNKNOWN_SCOPE' if conflict else 'UNKNOWN_ALIAS_SCOPE')
        aliases.append(dict(text=c['text'],parse_status=c['parsed_interpretation']['status'],comparison=comparison,claim_strength=strength))
    relevant={'tautomer specificity':'tautomer','charge/protonation':'protonation_charge','alias conflict':'multiple_source_claim_dimensions'}[r['blocker']]
    primary_code={'tautomer specificity':'SOURCE_TAUTOMER_SPECIFICITY_UNKNOWN','charge/protonation':'SOURCE_PROTONATION_SPECIFICITY_UNKNOWN','alias conflict':'SOURCE_CONSTITUTION_CONFLICT'}[r['blocker']]
    out.append(dict(record_id=r['cuma_index'],preferred_name=name,aliases=aliases,primary_blocker=r['blocker'],secondary_blockers=[x for x in reasons if x!=primary_code],all_reason_codes=reasons,opsin_candidate=r['candidate'],relevant_identity_dimension=relevant,suspected_nomenclature_patterns=patterns,source_appears_genuinely_specific=('EXPLICIT_HYDROGEN_TOKEN_SCOPE_UNMAPPED' if 'indicated_hydrogen_token_requires_locant_mapping' in patterns else 'NOT_DETERMINED_FROM_FROZEN_EVIDENCE'),general_rule_appears_possible='POSSIBLE_IF_SOURCE_ATOM_SCOPE_AND_OTHER_FORM_DIMENSIONS_ARE_VERIFIED',grounding_source_required=['IUPAC nomenclature and source-to-atom mapping','independent interpretation of each conflicting alias'],reference_smiles=r['reference_smiles'],source_claim_conflicts=r['source_form']['source_claim_conflicts']))
assert len({x['record_id'] for x in out})==81
(B/'NOMENCLATURE_FALSE_HOLD_TAXONOMY.json').write_text(json.dumps(out,indent=2,ensure_ascii=False),encoding='utf8')
print(json.dumps({'count':len(out),'primary_blockers':dict(collections.Counter(x['primary_blocker'] for x in out)),'nonexclusive_patterns':dict(collections.Counter(v for x in out for v in x['suspected_nomenclature_patterns']))},indent=2))
