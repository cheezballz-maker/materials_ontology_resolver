"""Function-local dependency injection; no monkeypatches or default changes."""
import bootstrap
import stereo_comparison as stereo
import source_identity_qualification as source
import candidate_identity_adapter as candidate
import identity_correspondence_comparator as pair
import correspondence_assessment as old
import diagnostic_resolver as original_resolver

clone=stereo.previous._copy_function
qualify_source=clone(source.qualify,reconcile=stereo.reconcile)
qualify_candidate=clone(candidate.qualify,reconcile=stereo.reconcile)
compare=clone(pair.compare,reconcile=stereo.reconcile)
represented_graphs=clone(old.represented_graphs,qualify_source=qualify_source,qualify_candidate=qualify_candidate,compare=compare)
_assess=clone(old.assess,qualify_source=qualify_source,qualify_candidate=qualify_candidate,compare=compare,represented_graphs=represented_graphs)
resolve_correspondence=clone(original_resolver.resolve_correspondence,qualify_source=qualify_source,qualify_candidate=qualify_candidate,compare=compare)

def assess(incoming,reference,*,enabled=False):
 # Keyword-only defaults are explicit here; cloned functions need no global
 # changes, but FunctionType does not carry __kwdefaults__ automatically.
 return _assess(incoming,reference,enabled=enabled)
