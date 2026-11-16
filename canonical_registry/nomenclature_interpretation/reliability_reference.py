"""Independent source-based provisional annotations. Never imports the resolver."""

from collections import defaultdict
import json
from pathlib import Path
import re

from rdkit import Chem

MODULES = (
    "molecular_chemical", "inorganic_mineral", "botanical", "biological_biotechnological",
    "polymer_silicone", "lipid_surfactant", "colorant", "preparation_mixture",
)
DATA = Path(__file__).with_name("evaluation") / "reliability_v1"
BASE = ("population", "challenge_1", "challenge_2", "challenge_3", "challenge_4")
PO = {"leaf": "0025034", "leaves": "0025034", "flower": "0009046", "flowers": "0009046",
      "root": "0009005", "roots": "0009005", "seed": "0009010", "seeds": "0009010",
      "stem": "0009047", "stems": "0009047", "fruit": "0009001", "fruits": "0009001"}
PARTS = set(PO) | {"bark", "rhizome", "peel", "bud", "shoot", "wood", "bulb", "whole plant", "kernel"}
BOTANICAL_FORMS = {"extract", "juice", "oil", "water", "powder", "wax", "distillate"}
MINERALS = {"kaolin", "kaolinite", "bentonite", "mica", "quartz", "calcite", "talc", "magnetite",
            "silica", "clay", "zeolite", "peat"}
METALS = {"aluminium", "aluminum", "barium", "calcium", "chromium", "cobalt", "copper", "iron",
          "lanthanum", "lithium", "magnesium", "manganese", "nickel", "potassium", "silver",
          "sodium", "strontium", "tin", "titanium", "zinc", "zirconium"}
ANIONS = {"fluoride", "chloride", "bromide", "iodide", "carbonate", "bicarbonate", "phosphate",
          "sulfate", "sulphate", "nitrate", "hydroxide"}
POLYMERS = {"copolymer", "crosspolymer", "terpolymer", "polymer", "silicone", "dimethicone",
            "polysiloxane", "polyethylene", "polypropylene", "nylon", "polyquaternium",
            "polyglyceryl", "polyglycerin", "polyurethane", "polysilsesquioxane", "cellulose"}
LIPID_TOKENS = set(("laurate stearate oleate isostearate palmitate myristate caprate caprylate "
                    "isodecanoate olivate glyceride glycerides triglyceride triglycerides diglyceride diglycerides "
                    "monoglyceride monoglycerides ethoxylated propoxylated plasmalogens sterol").split())
LIPID_ACID_ROOTS = set("caprylic capric lauric myristic palmitic stearic isostearic oleic linoleic fatty".split())
PREP_WORDS = set(("denat denatured hydrolyzed hydrolysed hydrogenated blend mixture juice extract distillate "
                  "preparation filtrate").split())
COLOR_FORMS = {"pigment", "dye", "colourant", "colorant", "lake"}
COLOR_CLASSES = set("acid basic direct disperse food mordant pigment reactive solvent sulfur vat".split())
COLOR_HUES = set("black blue brown green grey gray orange red violet white yellow".split())
# Independently transcribed controlled labels from Annex I of 2006/257/EC.
FUNCTIONS = set("""ABRASIVE;ABSORBENT;ANTICAKING;ANTICORROSIVE;ANTIDANDRUFF;ANTIFOAMING;ANTIMICROBIAL;
ANTIOXIDANT;ANTIPERSPIRANT;ANTIPLAQUE;ANTISEBORRHOEIC;ANTISTATIC;ASTRINGENT;BINDING;BLEACHING;BUFFERING;
BULKING;CHELATING;CLEANSING;COSMETIC COLORANT;DENATURANT;DEODORANT;DEPILATORY;DETANGLING;EMOLLIENT;
EMULSIFYING;EMULSION STABILISING;FILM FORMING;FOAMING;FOAM BOOSTING;GEL FORMING;HAIR CONDITIONING;
HAIR DYEING;HAIR FIXING;HAIR WAVING OR STRAIGHTENING;HUMECTANT;HYDROTROPE;KERATOLYTIC;MASKING;
MOISTURISING;NAIL CONDITIONING;OPACIFYING;ORAL CARE;OXIDISING;PEARLESCENT;PLASTICISER;PRESERVATIVE;
PROPELLANT;REDUCING;REFATTING;REFRESHING;SKIN CONDITIONING;SKIN PROTECTING;SMOOTHING;SOLVENT;SOOTHING;
STABILISING;SURFACTANT;TANNING;TONIC;UV ABSORBER;UV FILTER;VISCOSITY CONTROLLING""".replace("\n", "").split(";"))


def array(value):
    return (json.loads(value) if isinstance(value, str) else value) or []


def role_reference(label, index):
    text = " ".join(label.upper().split())
    terms = [("COSMETIC COLORANT" if part == "COLORANT" else part) for part in text.split(" - ")]
    valid = 1 <= len(terms) <= 2 and all(part in FUNCTIONS for part in terms)
    state = ("VOCABULARY_VALIDATED" if len(terms) == 1 else "VOCABULARY_COMPONENTS_VALIDATED") if valid else "LABEL_UNMAPPED"
    return {"reported_function": label, "application_context": "cosmetics", "qualification": state,
            "qualified_vocabulary_labels": terms if valid else [], "field": f"functions[{index}]"}


def graphs(aliases):
    """Normalize source representations only. No name parser or resolver is used."""
    values, failed = set(), []
    options = Chem.SmilesParserParams()
    options.parseName = False
    options.allowCXSMILES = False
    for row in aliases:
        kind, value = row["alias_type"], row["alias"]
        if kind not in ("SMILES", "INCHI"):
            continue
        try:
            mol = (Chem.MolFromSmiles(value, options) if kind == "SMILES" else Chem.MolFromInchi(value))
            if not mol or any(ord(c) <= 32 for c in value):
                failed.append(row["inci_alias_id"])
                continue
            values.add(Chem.MolToSmiles(mol, isomericSmiles=True))
        except (RuntimeError, ValueError):
            failed.append(row["inci_alias_id"])
    return sorted(values), failed


def annotate(row):
    name = row["inci"].casefold().strip()
    definition = (row.get("description") or "").casefold()
    raw_tokens = re.findall(r"[a-z]+(?:-\d+)?|\d+", name)
    words = set(raw_tokens)
    facts = defaultdict(list)
    holds = set()

    def add(module, predicate, value, scope="LABEL_FACET"):
        fact = [predicate, value, scope]
        if fact not in facts[module]:
            facts[module].append(fact)

    module = "preparation_mixture"
    for token in sorted(words & PREP_WORDS):
        add(module, "reported_preparation_qualifier", "denat." if token == "denat" and "denat." in name else token)
    for form in ("oil", "wax"):
        if raw_tokens and raw_tokens[-1] == form:
            qualifiers = {"seed", "leaf", "root", "flower", "stem", "essential", "vegetable"}
            prefix = raw_tokens[-2] if len(raw_tokens) > 1 else ""
            add(module, "reported_preparation_qualifier", f"{prefix} {form}" if form == "oil" and prefix in qualifiers else form)
    if found := re.search(r"\bis (?:a|the) ((?:complex )?mixture|blend) of\b", definition):
        add(module, "reported_source_preparation", found[1], "REPORTED_SOURCE_DEFINITION")
    if facts[module]:
        holds.add(module)

    module = "biological_biotechnological"
    for token in raw_tokens:
        if (token in {"protein", "proteins", "ferment", "fermentation", "enzyme", "lysate",
                      "hydrolysate", "hydrolyzate"} or re.search(r"peptides?(?:-\d+)?$", token)):
            add(module, "reported_biological_category", token)
    if facts[module]:
        holds.add(module)

    module = "botanical"
    # Require a plant signal in the original definition, or the designation's
    # plant anatomy grammar and the absence of a contrary organism signal.
    no_plant = bool(re.search(r"\b(coral|placenta|bacterium|yeast|alga|fungus)\b", name + " " + definition))
    head = raw_tokens[-1] if raw_tokens else ""
    plant_hint = bool(re.search(r"\b(plant|plants|tree|trees|botanical|[a-z]+aceae)\b", definition))
    if head in BOTANICAL_FORMS and len(raw_tokens) >= 3 and not no_plant:
        first = re.match(r"^([a-z-]+ [a-z-]+)(?:\s*\([^)]*\))?\s+(.*)$", name)
        if first and not set(first[1].split()) & {"hydrolyzed", "hydrogenated", "sodium", "calcium", "acid"}:
            stem = first[2].removesuffix(head).strip()
            named_parts = [x.strip() for x in stem.split("/")] if stem else []
            if len(named_parts) == 1 and named_parts[0] not in PARTS:
                tail = named_parts[0].split(maxsplit=1)
                if len(tail) == 2 and tail[1] in PARTS and tail[0] not in PARTS and plant_hint:
                    first_taxon = first[1] + " " + tail[0]
                    named_parts = tail[1:]
                else:
                    first_taxon = first[1]
            else:
                first_taxon = first[1]
            if (named_parts and all(part in PARTS for part in named_parts)) or (not named_parts and plant_hint):
                add(module, "reported_taxon_text", first_taxon, "UNVERIFIED_TAXON_TEXT")
                add(module, "reported_botanical_preparation", head)
                for part in named_parts:
                    add(module, "reported_plant_part", part, "REPORTED_SOURCE_PART")
                    if part in PO:
                        add(module, "source_anatomical_structure",
                            "http://purl.obolibrary.org/obo/PO_" + PO[part], "REPORTED_SOURCE_PART")
                holds.add(module)

    module = "polymer_silicone"
    for token in raw_tokens:
        word = token.split("-")[0]
        if word in POLYMERS:
            add(module, "reported_polymer_category", word)
    grade_matches = list(re.finditer(r"(?<![a-z])(?:peg/ppg[ -]\d+/\d+|(?:peg|ppg)[ -]\d+)\b", name))
    for grade in grade_matches:
        add(module, "reported_polyether_grade", grade[0])
    if facts[module]:
        holds.add(module)

    module = "lipid_surfactant"
    for i, token in enumerate(raw_tokens):
        if token in LIPID_TOKENS or re.fullmatch(r"(?:laureth|ceteareth|steareth|ceteth|oleth|pareth|trideceth)(?:-\d+)?", token):
            add(module, "reported_lipid_surfactant_qualifier", token)
        next_token = raw_tokens[i + 1] if i + 1 < len(raw_tokens) else ""
        if (token in LIPID_ACID_ROOTS and next_token in {"acid", "acids", "alcohol", "alcohols"}) or (
                token in {"cetyl", "stearyl", "cetearyl", "oleyl"} and next_token == "alcohol") or (
                token in {"lauryl", "myristyl", "stearyl"} and next_token in {"sulfate", "sulphate"}):
            add(module, "reported_lipid_surfactant_qualifier", token + " " + next_token)
    if any(re.search(r"glycerides$|^isostear|^(?:ethoxylated|propoxylated)$|(?:re|t)th-\d+$", fact[1])
           for fact in facts[module]) or (facts[module] and re.search(r"\bc\d+-\d+\b", name)):
        holds.add(module)

    module = "colorant"
    index = re.fullmatch(r"c\.?\s*i\.?\s*(\d{5,6}(?::\d+)?)", name)
    if index:
        add(module, "ColourIndex", index[1], "CANDIDATE_INDEX_DESIGNATION")
    else:
        color_text = re.sub(r"^c\.?\s*i\.?\s*", "", name) if name.startswith(("c.i.", "ci ")) else name
        match = re.match(r"^([a-z]+) ([a-z]+) (\d+(?::\d+)?)(.*)$", color_text)
        if match and match[1] in COLOR_CLASSES and match[2] in COLOR_HUES:
            add(module, "ColourIndexGenericName", " ".join(match.group(i) for i in (1, 2, 3)), "CANDIDATE_INDEX_DESIGNATION")
            if match[4].strip().endswith("lake"):
                add(module, "reported_colorant_qualifier", match[4].strip())
        elif words & COLOR_FORMS:
            for token in raw_tokens:
                if token in COLOR_FORMS:
                    add(module, "reported_colorant_qualifier", token)
                    break
    if facts[module]:
        holds.add(module)

    module = "inorganic_mineral"
    for token in raw_tokens:
        if token in MINERALS:
            add(module, "reported_mineral_name", token)
    mixed = re.fullmatch(r"(.+?)\s+((?:mon|di|tri|tetra)?oxides?)", name)
    if mixed:
        listed = [v.strip() for v in re.split(r"[/–-]", mixed[1])]
        if all(v in METALS for v in listed):
            if len(listed) == 1:
                add(module, "reported_oxide_name", name)
            else:
                add(module, "reported_inorganic_multimetal_oxide", name)
            holds.add(module)
    salt = re.fullmatch(r"([a-z]+)(?:\s*\([ivx]+\))? ([a-z]+)(?: (.+))?", name)
    if salt and salt[1] in METALS and salt[2] in ANIONS:
        suffix = salt[3] or ""
        if not suffix or suffix == "hydroxide" or suffix.endswith("hydrate") or suffix == "anhydrous":
            value = name if suffix == "hydroxide" else name.removesuffix(suffix).strip() if suffix else name
            add(module, "reported_inorganic_salt_name", value)
            if suffix == "hydroxide":
                holds.add(module)
    for token in raw_tokens:
        if token.endswith("hydrate") or token in ("hydrated", "anhydrous"):
            add(module, "reported_hydration_qualifier", token)
    if words & MINERALS:
        holds.add(module)

    graph_values, invalid = graphs(array(row.get("alias_claims")))
    for value in graph_values:
        add("molecular_chemical", "molecular_graph", value, "TYPED_CANDIDATE_GRAPH")
    routes = {m: bool(facts[m]) for m in MODULES}
    if not graph_values:
        routes["molecular_chemical"] = None if invalid or not holds else False
    for m in MODULES:
        if not facts[m] and row["stratum"] == m.upper().split("_")[0] and row["stratum"] != "MOLECULAR":
            # A sampling marker is not a positive. Reserve ambiguous misses
            # where evidence does not independently settle the target scope.
            if m not in {"inorganic_mineral", "botanical", "preparation_mixture"}:
                routes[m] = None
    roles = [role_reference(label, index) for index, label in enumerate(array(row.get("functions")))
             if isinstance(label, str) and label.strip()]
    referent = ("NONMOLECULAR_OR_UNSPECIFIED_MATERIAL" if holds else
                "TYPED_GRAPH_CANDIDATES_ONLY" if graph_values else "UNRESOLVED")
    return {"id": row["inci_id"], "name": row["inci"], "routes": routes, "assertions": dict(facts),
            "whole_referent_scope": referent, "scope_hold_modules": sorted(holds),
            "structure_evidence": "CANDIDATE_ONLY" if graph_values else "NOT_ESTABLISHED",
            "invalid_typed_rows": invalid, "uncertainty_required": True, "roles": roles,
            "fallback": False if any(v is True for v in routes.values()) else
            True if all(v is False for v in routes.values()) else None}
