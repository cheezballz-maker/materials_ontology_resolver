"""Do not let full component SMILES leak unknown form specificity into a decision.

Legacy component/ratio comparisons key components by complete isomeric SMILES.
They therefore depend on component isotope/stereo/tautomer/charge specificity.
An unresolved contributing form dimension cannot establish an exact component
identity or a difference solely through that composite key. No graph is changed.
"""
import copy
FORM_DIMENSIONS=('stereochemistry','isotope','tautomer','protonation_charge')
COMPOSITE_DIMENSIONS=('components','component_stoichiometry','hydration_solvation')
def comparison_view(assertions):
 out=copy.deepcopy(assertions)
 missing=[d for d in FORM_DIMENSIONS if d in out and out[d].get('state') in ('UNKNOWN','UNSPECIFIED','SET')]
 if missing:
  for d in COMPOSITE_DIMENSIONS:
   if d in out:out[d]={'state':'UNKNOWN','rule_id':'COMPOSITE_COMPONENT_FORM_DEPENDENCY_UNRESOLVED'}
 return out,missing
