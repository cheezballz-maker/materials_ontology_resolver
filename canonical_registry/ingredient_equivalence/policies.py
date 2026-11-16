"""Category-level identity slots and separately reportable material facets.

Slot values compare only within the same qualified scheme. A scheme must make
exclusive values genuinely incompatible. Material overlap and broad classifications
do not establish distinctness.
"""

from .contracts import Family

# These slots participate only when relevant to the governing definition and
# reviewed as exclusive. Descriptive differences never become contradictions.
SLOTS = {
    Family.MOLECULAR: ("ingredient_specification", "composition_scope"),
    Family.INORGANIC: ("phase", "particle_specification", "material_form", "composition_scope"),
    Family.METALLIC: ("grade_specification", "composition_scope", "processing_specification"),
    Family.COLORANT: ("pigment_preparation", "particle_specification", "material_form"),
    Family.BOTANICAL: ("taxon", "plant_part", "preparation", "processing_specification", "composition_scope"),
    Family.POLYMER: ("polymer_constituent_specification", "architecture", "repeat_unit_specification",
                    "copolymer_composition", "polymer_distribution", "end_group_specification", "grade_specification"),
    Family.LIPID: ("composition_scope", "chain_specification", "alkoxylation", "esterification",
                   "substitution_specification", "preparation"),
    Family.BIOLOGICAL: ("organism", "biological_class", "biological_specification",
                        "fermentation_specification", "preparation", "processing_specification"),
    Family.PREPARATION: ("constituent_specification", "composition_scope", "preparation",
                         "denaturing", "processing_specification"),
}
COMMON = ("ingredient_specification", "designation_scope", "regulatory_designation_scope", "defining_referent")
RELATED_FACETS = {
    "material": "SHARED_MATERIAL_REFERENT",
    "taxon": "SHARED_BOTANICAL_TAXON",
    "plant_part": "SHARED_PLANT_PART",
    "organism": "SHARED_SOURCE_ORGANISM",
    "constituent": "SHARED_CONSTITUENT",
    "preparation_source": "SHARED_PREPARATION_SOURCE",
    "repeat_unit_specification": "SHARED_REPEAT_UNIT",
    "polymer_family": "SHARED_POLYMER_FAMILY",
}
