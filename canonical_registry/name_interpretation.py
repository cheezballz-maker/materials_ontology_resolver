"""Source-only name interpretation; retrieval is deliberately not an input.

An interpretation is a provisional reading of a source claim, never proof that
the corresponding candidate may be admitted. External evidence passed through
the reserved interface is recorded but is not yet trusted for interpretation.
"""
from dataclasses import dataclass, asdict
import re
from chemistry import normalize_name
from form_characterizer import characterize
from source_form import source_claim
from systematic_notation import source_annotations,map_descriptors


@dataclass(frozen=True)
class NameInterpretationEvidence:
    name: str
    interpreted_form: object
    interpretation_status: str
    reference: str


def normalized_parse_query(name):
    """No chemical-name rewrite is currently supported."""
    return None


def interpret_preferred(name, claim, aliases=(), alternate_claim=None, evidence=None, cml_result=None):
    profile = source_claim(name, claim)
    notation=source_annotations(name)
    profile['nomenclature']=notation
    f = profile['source_features']
    # Alternate text is never allowed to establish source-name interpretation.
    selected = claim
    parsed = selected.get('status') == 'SUCCESS' and bool(selected.get('structure'))
    conflicting_aliases = []
    status, diagnostic = 'UNKNOWN', 'NAME_INTERPRETATION_UNKNOWN'
    if f['relative_stereo'] and not (f['absolute_stereo_descriptors'] or f['dl_descriptor']):
        status, diagnostic = 'PARTIAL', 'NAME_UNDERSPECIFIED'
    elif f['ensemble']:
        status, diagnostic = 'PARTIAL', 'NAME_UNDERSPECIFIED'
    elif parsed:
        form = characterize(selected['structure'])
        stereo = form['stereo_state']
        specified = any(x['state'] == 'Specified' for x in form['stereo_elements'])
        source_stereo = f['absolute_stereo_descriptors'] or f['geometric_configurations'] or f['dl_descriptor'] or f['relative_stereo']
        if stereo in ('UNSPECIFIED', 'PARTIAL'):
            status, diagnostic = 'PARTIAL', 'NAME_UNDERSPECIFIED'
        elif specified and not source_stereo:
            status, diagnostic = 'UNKNOWN', 'NAME_INTERPRETATION_UNKNOWN'
        else:
            status, diagnostic = 'ESTABLISHED', None
    elif re.search(r'\d\s*[,()-]|\([^)]*\d', name):
        diagnostic = 'NAME_NOTATION_UNSUPPORTED'
    mapping=None
    if parsed and notation['descriptors'] and cml_result is not None:
        mapping=map_descriptors(cml_result.get('cml',''),selected['structure']['smiles'],notation['descriptors']) if cml_result.get('status')=='SUCCESS' else dict(status='UNKNOWN',reason='CML_UNAVAILABLE',mappings=[])
        if mapping['status']!='MAPPED' and status not in ('CONFLICTING','PARTIAL'):
            status,diagnostic='UNKNOWN','NAME_NOTATION_UNSUPPORTED'
    profile['stereo_locant_mapping']=mapping
    result = dict(name=name, status=status, diagnostic=diagnostic,
                  interpreted_form=selected.get('structure', {}).get('smiles') if parsed else None,
                  reference='OPSIN source-name parse' if parsed else None,
                  parser_status=claim.get('status'),
                  normalized_parse_query=selected.get('original') if selected is alternate_claim and parsed else None,
                  conflicting_aliases=conflicting_aliases)
    if evidence is not None:
        result['unverified_future_evidence'] = asdict(evidence)
        result['future_evidence_applied'] = False
    return result, profile
