"""Bounded capabilities of the adapters, not provider reliability scores.

These profiles describe representational possibilities, not a guarantee that a
particular record retains a form. Per-record checks remain mandatory.
"""
from dataclasses import dataclass

@dataclass(frozen=True)
class ProviderCapabilityProfile:
    provider_name: str
    accepted_exact_lookup_routes: tuple
    available_structure_fields: tuple = ('SMILES', 'InChI', 'InChIKey')
    supports_stereo: bool = True
    supports_isotopes: bool = True
    supports_formal_charge: bool = True
    supports_multicomponent_structure: bool = True
    supports_explicit_hydrogen_or_protonation: bool = True
    tautomer_representation_behavior: str = 'NORMALIZED_OR_UNCERTAIN'
    known_structure_standardization_behavior: str = 'FORM_PRESERVATION_UNCERTAIN'
    record_identifier_types: tuple = ()
    source_independence_default: str = 'SOURCE_DEPENDENCE_UNKNOWN'

PROFILES = {
    'PubChem': ProviderCapabilityProfile('PubChem', ('name','PubChemCID','InChIKey'), record_identifier_types=('CID',), known_structure_standardization_behavior='PUBCHEM_STANDARDIZED'),
    'ChEBI': ProviderCapabilityProfile('ChEBI', ('name','ChEBIID','InChIKey'), record_identifier_types=('ChEBIID',)),
    'GSRS': ProviderCapabilityProfile('GSRS', ('name','UNII'), tautomer_representation_behavior='EXPLICIT_GRAPH', known_structure_standardization_behavior='VALIDATED_COMPLETE_MOIETIES', record_identifier_types=('record_id','UNII')),
    'CompTox': ProviderCapabilityProfile('CompTox', ('name','DTXSID','DTXCID','InChIKey','CASRegistryNumber'), record_identifier_types=('DTXSID','DTXCID'), known_structure_standardization_behavior='DSSTOX_REPRESENTATIVE_STRUCTURE'),
}
