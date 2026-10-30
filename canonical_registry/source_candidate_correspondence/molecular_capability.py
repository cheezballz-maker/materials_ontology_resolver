"""Reuse existing capability guards, separately from production admission."""
import bootstrap
from form_characterizer import interpret
CAPABILITY_REASONS={'INCHI_WARNING_REQUIRES_REVIEW','STEREO_UNSUPPORTED','STEREO_UNSPECIFIED','ELECTRONIC_STATE_UNSUPPORTED','UNSUPPORTED_ELEMENT_CAPABILITY','UNSUPPORTED_DISCRETE_STRUCTURE_CAPABILITY','UNSUPPORTED_COORDINATION_CAPABILITY'}
def inspect(descriptor):
 view=interpret(descriptor,'',{'explicit_structure':True})
 return view['features'],[r for r in view['reason_codes'] if r in CAPABILITY_REASONS]
