"""Prepare a read-only evidence view for a validated stereo refinement."""
from copy import deepcopy
from evidence_adapter_contract import evidence, ALL
from comparison_session import assertions


def refine_open_binding(adapted, qualified, selected, claims, trace, reconcile_graphs):
    """Keep the supplied claims and prioritize a compatible exact witness.

    A name cannot borrow a structure exemption. An already qualified exact
    structural field can retain its original authority in the projected view.
    """
    if (not qualified['binding_valid'] or qualified['source_conflicts']
            or qualified.get('dependent_internal_conflicts')
            or set(qualified['obligations']) - {
                'SOURCE_STEREOCHEMISTRY_UNSPECIFIED', 'SOURCE_IDENTITY_DIMENSIONS_INCOMPLETE',
                'INCHI_WARNING_REQUIRES_REVIEW', 'STEREO_UNSPECIFIED',
            } or selected.get('inchi_warning')
            or any(g.get('inchi_warning') not in ('', None, 'Omitted undefined stereo') for _, g in claims)
            or not any(k != 'name' for k, _ in claims)):
        return None
    normalized = deepcopy(adapted)
    incoming = normalized.incoming
    pkg = incoming.concept.evidence_package
    original_ids = incoming.concept.binding['evidence_ids']
    from comparison_session import descriptor
    from internal_structure_policy import authorized, _authorize
    trusted_warehouse = authorized(pkg)
    typed_witness = None
    for claim in pkg.claims:
        stereo = claim.dimension_assertions.get('stereochemistry', {})
        if claim.claim_role != 'STRUCTURAL_IDENTITY_ASSERTION' or not stereo:
            continue
        structures = claim.dimension_assertions.get('constitution', {}).get('structures', [])
        if len(structures) != 1:
            return None
        graph = descriptor(structures[0])
        if any(x['specified'] != 'Specified' for x in graph['stereo']):
            _, reason = reconcile_graphs(selected, graph)
            if reason != 'LEFT_MORE_SPECIFIC':
                return None
            # The original graph has no exact stereo assertion. The existing
            # isotope framework and composite component keys also include
            # stereo. Preserve all those assertions in provenance and remove
            # their redundant graph projections after the pair check above.
            from assertion_dependencies import COMPOSITE_DIMENSIONS
            claim.source_provenance['unified_open_form_before_refinement'] = {
                key: claim.dimension_assertions.pop(key)
                for key in ('stereochemistry', 'isotope', *COMPOSITE_DIMENSIONS) if key in claim.dimension_assertions
            }
        elif (claim.evidence_id in original_ids and graph['smiles'] == selected['smiles']
              and not claim.unresolved_dependencies
              and claim.source_provenance.get('origin') == 'SOURCE_PROVIDED'
              and claim.source_provenance.get('binding_policy') == 'BINDING_IDENTITY_ASSERTION'
              and any(k != 'name' and g['smiles'] == selected['smiles'] for k,g in claims)):
            typed_witness = claim
    parsed_names = [x['query'] for x in trace if x.get('provider') == 'OPSIN'
                    and x.get('smiles') == selected['smiles'] and x.get('status') == 'SUCCESS']
    if typed_witness:
        pkg.claims.remove(typed_witness)
        pkg.claims.insert(0, typed_witness)
        if trusted_warehouse:
            # Preserve the sealed authority only for an original, already
            # qualified exact field in the hash-verified package.
            _authorize(pkg)
        incoming.evidence_origin = 'UNIFIED_RECONCILED_SUPPLIED_STRUCTURES'
    else:
        if not parsed_names:
            return None
        c = evidence(pkg, 'unified_reconciled_name', 'CHEMICAL_NAME_ASSERTION', parsed_names[0],
                     'unified.name', binding='BINDING_IDENTITY_ASSERTION', basis='RULE_ESTABLISHED',
                     origin='DERIVED_SOURCE', assertions=assertions(selected['smiles']),
                     extra={'representation': 'OPSIN_NAME_RECONCILED_WITH_SUPPLIED_GRAPH',
                            'supporting_structure_evidence_ids': original_ids})
        pkg.add(c, ALL)
        pkg.claims.insert(0, pkg.claims.pop())
        incoming.concept.binding = {**incoming.concept.binding, 'kind': 'QUALIFIED_NAME_IDENTITY',
                                    'evidence_ids': [c.evidence_id, *original_ids]}
        incoming.evidence_origin = 'UNIFIED_DERIVED_NAME_RECONCILIATION'
    incoming.official_validation = None  # Recompute on the refined graph.

    class ReadOnlyEvidenceAdapter:
        def adapt(self, _source):
            return deepcopy(normalized)

    return ReadOnlyEvidenceAdapter()
