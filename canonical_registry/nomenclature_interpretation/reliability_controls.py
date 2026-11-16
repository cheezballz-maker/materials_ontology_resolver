"""Frozen adversarial inputs and equivalence transformations for reliability v1."""

from dataclasses import dataclass, replace
import random

from .contracts import Evidence, InterpretationInput, ReportedFunction, ReportedIdentifier, StructureKind, TypedStructure


def item(name, structures=(), ids=(), definition=None, functions=()):
    source = "benchmark:referent"
    return InterpretationInput(
        Evidence(name, "designation", source),
        tuple(TypedStructure(StructureKind(kind), Evidence(value, f"alias:{i}", source))
              for i, (kind, value) in enumerate(structures)),
        tuple(ReportedIdentifier(kind, Evidence(value, f"identifier:{i}", source))
              for i, (kind, value) in enumerate(ids)),
        tuple(ReportedFunction(Evidence(label, f"role:{i}", source), context, reference)
              for i, (label, context, reference) in enumerate(functions)),
        Evidence(definition, "definition", source) if definition else None,
    )


@dataclass(frozen=True)
class Control:
    key: str
    family: str
    sample: InterpretationInput
    must: tuple[tuple[str, object], ...] = ()
    forbid: tuple[str, ...] = ()
    route: str | None = None
    issue: str | None = None
    severity: str = "MAJOR"
    role_states: tuple[str, ...] | None = None
    note: str = ""


C = Control
S = "smiles"
I = "inchi"
CONTROLS = (
    C("specified_water", "molecular", item("water"), route="SUBSTANCE", severity="MINOR"),
    C("open_stereochemistry", "molecular", item("butan-2-ol"), route="CHEMICAL_CONCEPT", severity="CRITICAL"),
    C("positional_ambiguity", "molecular", item("aminobutyric acid", [(S, "NCCCC(=O)O")]),
      severity="CRITICAL"),
    C("unbound_hydrochloride", "molecular", item("methylamine hydrochloride", [(S, "CN")]),
      severity="CRITICAL", note="A free base graph must not establish the claimed salt."),
    C("named_counterions_conflict", "molecular", item("disodium malonate", [(S, "O=C(O)CC(=O)[O-].[Na+]")]),
      issue="GRAPH_DISAGREES_WITH_NAMED_COMPOSITION", severity="CRITICAL"),
    C("reported_hydrate", "molecular", item("calcium chloride dihydrate", [(S, "[Ca+2].[Cl-].[Cl-]")]),
      must=(("reported_hydration_qualifier", "dihydrate"),), severity="CRITICAL"),
    C("solvate_conflict", "molecular", item("ethanol methanol solvate", [(S, "CCO.CO"), (S, "CCO")]),
      severity="CRITICAL"),
    C("smiles_inchi_conflict", "molecular", item("water", [(S, "O"), (I, "InChI=1S/CH4/h1H4")]),
      issue="CONFLICTING_STRUCTURE_DIMENSIONS", severity="CRITICAL"),
    C("wrong_inchikey", "molecular", item("water", ids=[("InChIKey", "VNWKTOKETHGBQD-UHFFFAOYSA-N")]),
      issue="INCHIKEY_DISAGREES_WITH_ALL_GRAPHS", severity="CRITICAL"),
    C("wrong_formula", "molecular", item("water", ids=[("MolecularFormula", "C2H6O")]),
      issue="MOLECULAR_FORMULA_DISAGREES_WITH_ALL_GRAPHS", severity="CRITICAL"),
    C("misbound_exact_description", "molecular", item("water", definition="Water is ethanol."),
      issue="SOURCE_DEFINITION_DISAGREES_WITH_NAME_GRAPH", severity="CRITICAL"),
    C("constituent_clause", "molecular", item("water", definition="Water is a mixture of water and ethanol."),
      forbid=("molecular_graph",), severity="CRITICAL"),
    C("malformed_typed_alias", "molecular", item("water", [(S, "InChI=1S/H2O/h1H2")]),
      issue="TYPED_STRUCTURE_NOT_VALIDATED", severity="CRITICAL"),
    C("malformed_trailing_text", "molecular", item("water", [(S, "O ignored")]),
      issue="TYPED_STRUCTURE_NOT_VALIDATED", severity="CRITICAL"),
    C("carbonate_graph_serializations", "inorganic", item("sodium carbonate",
      [(S, "[Na+].[Na+].[O-]C(=O)[O-]"), (S, "O=C([O-])[O-].[Na+].[Na+]")]),
      must=(("reported_inorganic_salt_name", "sodium carbonate"),),
      note="The two supplied graphs differ only in serialization."),
    C("inorganic_nominal_formula_not_proof", "inorganic", item("titanium dioxide",
      [(S, "O=[Ti]=O"), (S, "[Ti+4].[O-2].[O-2]")]), forbid=("molecular_graph",),
      severity="CRITICAL", note="A shared formula does not establish material form or equivalence."),
    C("mixed_oxide", "inorganic", item("aluminium/magnesium/zinc oxide"),
      must=(("reported_inorganic_multimetal_oxide", "aluminium/magnesium/zinc oxide"),),
      forbid=("reported_oxide_name",)),
    C("hyphenated_mixed_oxide", "inorganic", item("magnesium-zinc oxide"),
      forbid=("reported_oxide_name",), note="A final metal token does not denote the whole mixed oxide."),
    C("phase_particle_scope", "inorganic", item("titanium dioxide rutile nanoparticulate", [(S, "O=[Ti]=O")]),
      must=(("reported_inorganic_material_form", "rutile"),), forbid=("molecular_graph",), severity="CRITICAL"),
    C("organic_amine_oxide", "inorganic", item("dihydroxyethyl tallowamine oxide"),
      forbid=("reported_oxide_name", "reported_inorganic_salt_name")),
    C("ambiguous_botanical", "botanical", item("orange oil"), forbid=("source_anatomical_structure", "reported_taxon_text")),
    C("botanical_synonym_is_candidate", "botanical", item("Aloe barbadensis leaf juice",
      definition="Aloe barbadensis is a botanical name used for Aloe vera."),
      must=(("reported_taxon_text", "Aloe barbadensis"), ("source_anatomical_structure", "http://purl.obolibrary.org/obo/PO_0025034"))),
    C("nonbotanical_binomial", "botanical", item("Bacillus subtilis root extract",
      definition="Bacillus subtilis root extract is an extract of a bacterium."),
      forbid=("reported_taxon_text", "source_anatomical_structure")),
    C("plant_part_embedded_unrelated", "botanical", item("sodium chloride root extract"),
      forbid=("source_anatomical_structure",)),
    C("multiple_botanical_parts", "botanical", item("Rosa canina fruit/seed oil"),
      must=(("reported_plant_part", "fruit"), ("reported_plant_part", "seed"), ("reported_botanical_preparation", "oil"))),
    C("botanical_juice", "botanical", item("Sambucus nigra flower juice"),
      must=(("reported_botanical_preparation", "juice"),)),
    C("botanical_extract", "botanical", item("Sambucus nigra flower extract"),
      must=(("reported_botanical_preparation", "extract"),)),
    C("ferment_constituent_graph", "biological", item("Saccharomyces/ethanol ferment filtrate", [(S, "CCO")]),
      must=(("reported_biological_category", "ferment"),), forbid=("molecular_graph",), severity="CRITICAL"),
    C("peptide_grade", "biological", item("SH-oligopeptide-24"), must=(("reported_biological_category", "oligopeptide-24"),)),
    C("copolymer_segments", "polymer", item("acrylates/vinyl acetate copolymer", [(S, "CC(=O)OC=C")]),
      must=(("reported_polymer_name_segments", "acrylates/vinyl acetate"),), forbid=("molecular_graph",), severity="CRITICAL"),
    C("unqualified_copolymer", "polymer", item("copolymer commercial grade A"), must=(("reported_polymer_category", "copolymer"),)),
    C("peg_ppg", "polymer", item("PEG/PPG-23/23 dimethicone"), must=(("reported_polyether_grade", "PEG/PPG-23/23"),)),
    C("chain_distribution", "lipid", item("C11-15 pareth-3 oleate", [(S, "CCCCCCCCCCCCCCCCCC(=O)O")]),
      must=(("reported_lipid_surfactant_qualifier", "oleate"),), severity="CRITICAL"),
    C("branched_acid_scope", "lipid", item("lauryl isostearate"), forbid=("molecular_graph",), severity="CRITICAL"),
    C("lipid_collective", "lipid", item("corn glycerides", [(S, "OCC(O)CO")]),
      must=(("reported_lipid_surfactant_qualifier", "glycerides"),), forbid=("molecular_graph",), severity="CRITICAL"),
    C("colour_five_digits", "colorant", item("CI 77891", [(S, "O=[Ti]=O")], [("CAS", "13463-67-7")]),
      must=(("ColourIndex", "77891"),), forbid=("molecular_graph",), severity="CRITICAL"),
    C("colour_six_digits", "colorant", item("C.I.123456:2"), must=(("ColourIndex", "123456:2"),)),
    C("colour_generic_lake", "colorant", item("Acid Blue 9 Aluminum Lake"),
      must=(("ColourIndexGenericName", "Acid Blue 9"), ("reported_colorant_qualifier", "Aluminum Lake"))),
    C("invalid_colour_identifier", "colorant", item("CI 7789"), forbid=("ColourIndex",)),
    C("denatured_not_ethanol", "preparation", item("alcohol denat.", [(S, "CCO")], [("CAS", "64-17-5"), ("EC", "200-578-6")]),
      forbid=("molecular_graph",), severity="CRITICAL"),
    C("unknown_designation", "fallback", item("unclassified QZ item"), note="The generic route must retain the original designation."),
    C("context_and_unknown_role", "role", item("water", functions=[
      ("COLORANT", "cosmetics", None), ("COLORANT", "cosmetics", None),
      ("SURFACTANT - CLEANSING", "cosmetics", None), ("UNKNOWN PURPOSE", "cosmetics", None),
      ("COLORANT", "cosmetics", "urn:invented:vocabulary"), ("COLORANT", "food", "urn:invented:vocabulary")]),
      route="SUBSTANCE", role_states=("VOCABULARY_VALIDATED", "VOCABULARY_VALIDATED",
      "VOCABULARY_COMPONENTS_VALIDATED", "LABEL_UNMAPPED", "VOCABULARY_REFERENCE_UNVERIFIED", "REPORTED")),
)

CONFIRMATION_CONTROLS = (
    C("different_formula_conflict", "molecular", item("ethanol", ids=[("MolecularFormula", "CH4O")]),
      issue="MOLECULAR_FORMULA_DISAGREES_WITH_ALL_GRAPHS", severity="CRITICAL"),
    C("composition_order_equivalence", "molecular", item("ethanol", ids=[("MolecularFormula", "H6C2O")]),
      route="SUBSTANCE", severity="CRITICAL"),
    C("formula_hydrate_not_reduced", "molecular", item("ethanol", ids=[("MolecularFormula", "C2H6O·H2O")]),
      issue="MOLECULAR_FORMULA_COMPARISON_INCOMPLETE", severity="CRITICAL"),
    C("different_definition_conflict", "molecular", item("methanol", definition="Methanol is acetone."),
      issue="SOURCE_DEFINITION_DISAGREES_WITH_NAME_GRAPH", severity="CRITICAL"),
    C("definition_synonym", "molecular", item("ethanol", definition="Ethanol is ethyl alcohol."),
      route="SUBSTANCE", severity="CRITICAL"),
    C("fungal_plant_part_collision", "botanical", item("Aspergillus niger leaf extract",
      definition="Aspergillus niger leaf extract is an extract of a fungus."),
      forbid=("source_anatomical_structure", "reported_taxon_text")),
    C("en_dash_mixed_oxide", "inorganic", item("copper–zinc oxide"),
      must=(("reported_inorganic_multimetal_oxide", "copper–zinc oxide"),), forbid=("reported_oxide_name",)),
    C("oil_in_derived_material", "preparation", item("Camellia sinensis seed oil PEG-8 esters"),
      must=(("reported_preparation_source_phrase", "seed oil"),), forbid=("reported_preparation_qualifier",)),
)


def equivalent_variant(original, iteration):
    """Keep each source pointer attached to its value when changing order."""
    rng = random.Random(521071 + iteration)
    def reorder(values):
        result = list(values)
        if iteration == 0:
            result.reverse()
        else:
            rng.shuffle(result)
        return tuple(result)
    return replace(original, structures=reorder(original.structures), identifiers=reorder(original.identifiers),
                   functions=reorder(original.functions))


def duplicate_evidence(original):
    return replace(original, structures=original.structures + original.structures[:1],
                   identifiers=original.identifiers + original.identifiers[:1],
                   functions=original.functions + original.functions[:1])
