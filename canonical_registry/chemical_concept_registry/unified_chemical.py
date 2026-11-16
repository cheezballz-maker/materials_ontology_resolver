"""Bounded v1.1 router over existing concept and Substance services.

Substance matching requires an existing qualified source adapter. Name parsing
generates structural evidence, not authority for exact identity creation.
"""
import hashlib
import json
import time
from pathlib import Path
from constraints import ProposalError, molecular, compare_graphs, compare_stereo
from chemistry import describe
from rdkit import Chem

VERSION = 'chemical-concept-unified-1.1-validation'

def _open(graph):
    return sum(x['specified'] != 'Specified' for x in graph['stereo'])

def reconcile_graphs(a, b):
    """Return the more specific compatible view, never synthesize a hybrid."""
    dims = compare_graphs(a, b)['dimensions']
    keys = ('connectivity','protonation_charge','isotope_specification',
            'tautomeric_form','electronic_state','components','component_stoichiometry')
    if any(dims[k] == 'DIFFERENT' for k in keys):
        return None, 'CONFLICTING_STRUCTURE_DIMENSIONS'
    if any(dims[k] not in ('EQUIVALENT','NOT_APPLICABLE') for k in keys):
        return None, 'STRUCTURE_COMPARISON_INCOMPLETE'
    stereo=compare_stereo(a['smiles'],b['smiles'])
    if stereo['result']=='DIFFERENT':return None,'CONFLICTING_STEREOCHEMISTRY'
    if stereo['reason'] not in ('STEREO_NOT_APPLICABLE','ALL_RELEVANT_STEREO_SUPPORTED','STEREO_SPECIFICITY_UNKNOWN'):
        return None,'STEREO_COMPARISON_INCOMPLETE'
    if not _open(a) and not _open(b):
        return (a,'COMPATIBLE') if stereo['result'] in ('EQUIVALENT','NOT_APPLICABLE') else (None,'STEREO_COMPARISON_INCOMPLETE')
    try:
        # Complete bounded isomer sets establish containment; no assumptions
        # about symmetry or open features are made from a count alone.
        aa=set(molecular(a['smiles'])['isomers']) if _open(a) else {a['smiles']}
        bb=set(molecular(b['smiles'])['isomers']) if _open(b) else {b['smiles']}
    except ProposalError as exc:return None,exc.code
    if aa==bb:return a,'COMPATIBLE'
    if aa < bb:return a,'LEFT_MORE_SPECIFIC'
    if bb < aa:return b,'RIGHT_MORE_SPECIFIC'
    if not aa.intersection(bb):return None,'CONFLICTING_STEREOCHEMISTRY'
    return None,'OVERLAPPING_STEREO_CONSTRAINTS_UNRESOLVED'

class UnifiedChemicalResolver:
    def __init__(self, concept_registry, substance_registry, *, name_adapter=None, substance_resolver=None):
        self.concepts=concept_registry
        self.substance_registry=substance_registry if hasattr(substance_registry,'assert_unchanged') else Path(substance_registry)
        self.name_adapter=name_adapter
        self.substance_resolver=substance_resolver

    def resolve(self, source, *, source_adapter=None, request_key=None, create_concept=True, retrieval_policy=None):
        t=time.perf_counter()
        result=dict(outcome='UNRESOLVED',substance_id=None,concept_id=None,
                    interpretation=None,validation='NOT_ESTABLISHED',evidence=[],diagnostics=[],
                    resolver_version=VERSION,substance_creation='DISABLED',
                    substance_comparisons=0,concept_comparisons=0,registry_snapshot=None)
        def finish(code,reason=None):
            result['outcome']=code
            if reason:result['diagnostics'].append(reason)
            # The digest is a post-operation observation, not an atomic
            # cross-database snapshot or a guarantee against later writes.
            try:
                with self.concepts.path.open('rb') as stream:
                    result['concept_registry_snapshot']={'path':str(self.concepts.path),'sha256':hashlib.file_digest(stream,'sha256').hexdigest()}
            except OSError:
                result['concept_registry_snapshot']={'status':'UNAVAILABLE'}
            result['elapsed_seconds']=round(time.perf_counter()-t,6)
            return result
        raw=source.get('record',source)
        associated_names=set()
        if source_adapter is not None:
            try:
                adapted=source_adapter.adapt(source)
                attributes=adapted.incoming.concept.evidence_package.source_attributes
                associated_names={c.original_value for c in adapted.incoming.concept.evidence_package.claims
                                  if c.claim_role=='REPORTED_NAME_ASSOCIATION'
                                  and c.source_provenance.get('binding_policy')=='NONBINDING_ASSOCIATION'
                                  and isinstance(c.original_value,str)}
                blockers=attributes.get('internal_validation_blockers',[])
                if blockers:
                    result['evidence'].append({'module':'source_adapter','blockers':blockers})
                    return finish('CONFLICT' if any('CONTRADICTION' in x for x in blockers) else 'UNRESOLVED','SOURCE_ASSERTION_BLOCKED')
            except Exception as exc:return finish('UNRESOLVED','SOURCE_ADAPTER_FAILED:'+type(exc).__name__)
        if raw.get('family_key'):
            return finish('NONCANONICAL_BROAD_TERM','FAMILY_DEFINITION_EXCLUDED')
        names=list(dict.fromkeys(raw[k] for k in ('name','substance_master_name_en','iupac_name','jchem_name','compound_name','scientificname','cheman_name_en','cas_scientificname','inci_name') if isinstance(raw.get(k),str) and raw[k].strip()))
        name=names[0] if names else ''
        try:
            material=raw.get('material_class') or {}
            material=json.loads(material) if isinstance(material,str) else material
            if isinstance(material,dict) and material.get('material_class_l1') in ('Polymer','Metal/Alloy','Ceramic','Mineral','Mixture','Variable-composition material','Biological preparation','Crystalline phase'):
                return finish('UNRESOLVED','UNSUPPORTED_MATERIAL_SCOPE')
            flags=raw.get('substance_composition_classes') or {}
            flags=json.loads(flags) if isinstance(flags,str) else flags
            if isinstance(flags,dict) and any(flags.get(k) in (1,'1',True) for k in ('polymer','alloy','mineral','ceramic','tabular_inorganic','mixture','variable_composition','biological_preparation','crystalline_phase')):
                return finish('UNRESOLVED','UNSUPPORTED_MATERIAL_SCOPE')
        except (ValueError,TypeError):return finish('UNRESOLVED','MATERIAL_SCOPE_UNINTERPRETABLE')
        fields=[(k,raw.get(k)) for k in ('smiles','isometric_smiles','jchem_smiles','inchi','inchi_id') if raw.get(k)]
        if not fields and names:
            return finish('UNRESOLVED','NAME_DERIVED_STRUCTURE_REQUIRES_QUALIFIED_EVIDENCE')
        if source_adapter is None and any(raw.get(k) for k in ('cas','casrn','CASRegistryNumber','ec_number','pubchem_cid','chebi_id')):
            return finish('UNRESOLVED','EXTERNAL_IDENTIFIER_REQUIRES_QUALIFIED_EVIDENCE')
        claims=[]
        for key,value in fields:
            try:g=describe(value,'inchi' if key in ('inchi','inchi_id') else 'smiles')
            except (ValueError,RuntimeError):return finish('UNRESOLVED','INVALID_OR_UNSUPPORTED_'+key.upper())
            claims.append((key,g));result['evidence'].append({'field':key,'smiles':g['smiles']})
        unparsed_associations=[]
        for name_claim in names:
            if self.name_adapter is None:return finish('UNRESOLVED','NAME_INTERPRETATION_UNAVAILABLE')
            try: response=self.name_adapter.opsin(name_claim)
            except Exception:return finish('UNRESOLVED','NAME_INTERPRETATION_FAILED')
            result['evidence'].append({'field':'name','query':name_claim,'provider':'OPSIN','status':response.get('status'),'diagnostic':response.get('diagnostic','')})
            if response.get('status')!='SUCCESS':
                if response.get('status')=='FAILURE' and name_claim in associated_names and name_claim!=raw.get('name'):
                    unparsed_associations.append(name_claim)
                    result['evidence'][-1]['disposition']='UNPARSED_NONBINDING_ASSOCIATION'
                    continue
                return finish('UNRESOLVED','NAME_NOT_DETERMINISTICALLY_INTERPRETED')
            try:
                g=describe(response['smiles'])
                claims.append(('name',g))
                result['evidence'][-1].update(smiles=g['smiles'],inchi_warning=g.get('inchi_warning'))
            except (ValueError,RuntimeError):return finish('UNRESOLVED','NAME_DERIVED_GRAPH_INVALID')
        if not claims:return finish('UNRESOLVED','NO_INTERPRETABLE_STRUCTURE')
        selected=claims[0][1]
        for label,graph in claims[1:]:
            chosen,reason=reconcile_graphs(selected,graph)
            result['evidence'].append({'field':label,'comparison':reason,'smiles':graph['smiles'],
                                       'dimensions':compare_graphs(selected,graph)['dimensions'] if chosen is None else None})
            if chosen is None:return finish('CONFLICT' if reason.startswith('CONFLICTING_') else 'UNRESOLVED',reason)
            selected=chosen
        # Key belongs to the supplied graph; unassigned graph can coexist with
        # a more specific name. Never trust a key without a matching graph.
        supplied_keys=[raw[k] for k in ('inchikey','inchi_key') if raw.get(k)]
        if any(not any(g['inchikey']==value for _,g in claims) for value in supplied_keys):
            return finish('CONFLICT','SUPPLIED_INCHIKEY_STRUCTURE_MISMATCH')
        if source_adapter is None and raw.get('mol_formula') and not any(raw['mol_formula']==g['formula'] for _,g in claims):
            return finish('UNRESOLVED','SUPPLIED_FORMULA_REQUIRES_RECONCILIATION')
        if unparsed_associations and (_open(selected) or not any(k!='name' and g['smiles']==selected['smiles'] for k,g in claims)):
            return finish('UNRESOLVED','UNPARSED_ASSOCIATION_WITHOUT_EXACT_STRUCTURE')
        result['interpretation']={'smiles':selected['smiles'],'inchi':selected['inchi'],'inchikey':selected['inchikey'],
          'formula':selected['formula'],'charge':selected['charge'],'components':selected['components'],
          'stereo':selected['stereo'],'scope':'DISCRETE_MOLECULAR_GRAPH_NOT_MATERIAL_PHASE'}
        result['validation']='STRUCTURE_AND_SUPPLIED_CLAIMS_RECONCILED'
        if not _open(selected):
            if self.substance_resolver is None or source_adapter is None:
                return finish('UNRESOLVED','QUALIFIED_SUBSTANCE_ADAPTER_REQUIRED')
            # The raw interpretation and the qualified matcher evidence must
            # describe the same exact identity; an unrelated adapter result
            # cannot authorize routing a different graph to a canonical ID.
            from comparison_session import qualify_source
            qualified=qualify_source(adapted.incoming.concept)
            result['source_qualification']={k:qualified[k] for k in ('state','binding_valid','graph_view','obligations','source_conflicts')}
            if qualified.get('source_conflicts'):return finish('CONFLICT','SOURCE_EVIDENCE_CONFLICT')
            qualified_graph=qualified.get('graph_view')
            if not qualified_graph:return finish('UNRESOLVED','QUALIFIED_GRAPH_UNAVAILABLE')
            try: bound=describe(qualified_graph)
            except (ValueError,RuntimeError):return finish('UNRESOLVED','QUALIFIED_GRAPH_INVALID')
            _,binding_reason=reconcile_graphs(selected,bound)
            adapter=source_adapter
            if binding_reason=='LEFT_MORE_SPECIFIC' and _open(bound):
                from unified_qualification import refine_open_binding
                try:adapter=refine_open_binding(adapted,qualified,selected,claims,result['evidence'],reconcile_graphs)
                except (ValueError,RuntimeError):adapter=None
                if adapter is None:
                    return finish('UNRESOLVED','EXACT_REFINEMENT_NOT_QUALIFIED')
            elif binding_reason!='COMPATIBLE' or _open(bound):
                return finish('UNRESOLVED','QUALIFIED_GRAPH_DOES_NOT_ESTABLISH_SAME_EXACT_IDENTITY')
            r=self.substance_resolver.resolve(source,adapter,self.substance_registry,
                    persist_association=False,allow_creation=False,diagnostic_verbosity='summary',retrieval_policy=retrieval_policy)
            match=r.get('registry_match',{});ret=r.get('candidate_retrieval',{})
            result['registry_snapshot']=ret.get('snapshot_sha256')
            result['substance_comparisons']=match.get('uniqueness',{}).get('compared',0)
            result['substance_search']={'retrieval':ret,'match':match,'comparisons':r.get('chemical_comparison',[]),
                'admission_eligible':r.get('admission',{}).get('admission_eligible',False),
                'reconciliation':r.get('reconciliation'),'official_validation':r.get('admission',{}).get('official_validation'),
                'error':r.get('error')}
            result['evidence'].append({'module':'SubstanceResolver','status':r.get('resolution_status'),'reason_codes':r.get('reason_codes',[])})
            if r.get('resolution_status')=='SOURCE_CONFLICT':return finish('CONFLICT','SOURCE_EVIDENCE_CONFLICT')
            if r.get('admission',{}).get('existing_policy_result',{}).get('status')=='CONFLICT':
                return finish('CONFLICT','SUBSTANCE_ADMISSION_CONFLICT')
            if ret.get('search_complete') is False and r.get('admission',{}).get('admission_eligible') and match.get('uniqueness',{}).get('source_sufficient') and match.get('status')=='MATCH_UNRESOLVED':
                return finish('SUBSTANCE_SEARCH_INCOMPLETE','CANDIDATE_RETRIEVAL_TRUNCATED' if ret.get('truncated') else 'SNAPSHOT_COVERAGE_INCOMPLETE')
            if (r.get('resolution_status')=='EXACT_MATCH' and r.get('canonical_substance_id')
                    and match.get('uniqueness',{}).get('all_registry_records_examined')
                    and r.get('admission',{}).get('admission_eligible')):
                result['substance_id']=r.get('canonical_substance_id');return finish('EXACT_SUBSTANCE_MATCH')
            if r.get('resolution_status')=='NO_MATCH_IN_REGISTRY' and match.get('uniqueness',{}).get('all_registry_records_examined') and r.get('admission',{}).get('admission_eligible'):
                return finish('EXACT_SUBSTANCE_NOT_IN_REGISTRY','CREATION_DISABLED')
            return finish('UNRESOLVED','SUBSTANCE_MATCH_OR_ADMISSION_INCOMPLETE')
        try:definition=molecular(selected['smiles'])
        except ProposalError as exc:return finish('UNRESOLVED',exc.code)
        result['interpretation']['stereo_state']='UNASSIGNED_IN_REPRESENTATION'
        result['interpretation']['enumerated_isomers']=len(definition['isomers'])
        proposal={'kind':'molecular','smiles':selected['smiles']}
        if not create_concept:
            evaluated=self.concepts.propose(proposal);result['concept_comparisons']=len(evaluated['comparisons'])
            if len(evaluated['matches'])==1 and not evaluated['unresolved']:
                result['concept_id']=evaluated['matches'][0];return finish('CHEMICAL_CONCEPT_REUSED','READ_ONLY_PROPOSAL')
            return finish('UNRESOLVED','CONCEPT_CREATION_DISABLED_OR_COMPARISON_INCOMPLETE')
        if not request_key:return finish('UNRESOLVED','IDEMPOTENCY_KEY_REQUIRED')
        label=name or selected['smiles']
        audit={'source_record_id':raw.get('substance_id') or source.get('source_record_id'),
               'resolver_version':VERSION,'claims':result['evidence']}
        try:receipt=self.concepts.create_or_reuse(proposal,label,request_key,evidence=audit)
        except (ValueError,RuntimeError,PermissionError) as exc:return finish('UNRESOLVED','CONCEPT_TRANSACTION_FAILED:'+str(exc))
        result['concept_comparisons']=receipt.get('comparisons',0)
        if receipt['outcome']=='WITHHELD':return finish('UNRESOLVED','CONCEPT_COMPARISON_INCOMPLETE')
        result['concept_id']=receipt.get('concept_id')
        if receipt['outcome']=='CREATED':return finish('CHEMICAL_CONCEPT_CREATED')
        return finish('CHEMICAL_CONCEPT_REUSED','IDEMPOTENT_REPLAY' if receipt['outcome']=='IDEMPOTENT_REPLAY' else None)
