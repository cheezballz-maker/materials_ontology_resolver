"""Bounded nomenclature interpreters for material designations and qualifiers."""

import re

from .contracts import Assertion, Category, EvidenceRole, Issue, ModuleResult, State

_AQUEOUS_STEAM_DISTILLATE = re.compile(
    r"\baqueous\s+(?:solution|preparation)\s+of\s+(?:the\s+)?steam distillates?\b",re.I
)


def _assert(item, predicate, value, convention, *, category=Category.MATERIAL,
            role=EvidenceRole.DEFINING, evidence=None, slot=None, depends_on=()):
    # DEFINING at the lexical facet only, never evidence of canonical identity.
    return Assertion(category, predicate, value, role, evidence or item.designation, convention, slot, depends_on)


_FINAL_FORM = re.compile(r"\b(?P<form>extract|juice|oil|powder)\s*$",re.I)
_DEFINITION_FORM = re.compile(r"\b(?:is|are) (?:an? |the )?(?P<form>extract|juice|oil|powder) (?:of|from)\b",re.I)


def _disputed_form(item):
    name = _FINAL_FORM.search(item.designation.original_value)
    definition = item.source_definition
    source = _DEFINITION_FORM.search(definition.original_value) if definition else None
    return source["form"].casefold() if name and source and name["form"].casefold()!=source["form"].casefold() else None


class InorganicMineral:
    _metal = r"(?:alumini?um|aluminum|barium|calcium|chromium|cobalt|copper|iron|lanthanum|lithium|magnesium|manganese|nickel|potassium|silver|sodium|strontium|tin|titanium|zinc|zirconium)"
    _mineral = re.compile(r"\b(?:kaolin|kaolinite|bentonite|mica|quartz|calcite|talc|magnetite|silica|clay|zeolite)\b", re.I)
    _oxide = re.compile(
        r"\b(?:aluminium|aluminum|copper|iron|magnesium|silicon|titanium|zinc)"
        r"(?:\s*\([IVX]+\))?\s+(?:mon|di|tri|tetra)?oxides?\b",re.I
    )
    _additional_oxide = re.compile(
        rf"^\s*(?:{_metal}|silicon|thorium)(?:\s*\([IVX]+\))?\s+"
        r"(?:mon|di|tri|tetra)?oxides?(?=\s*$|\s+\((?:nano|rutile|anatase)\)\s*$)", re.I
    )
    _mixed_oxide = re.compile(
        rf"\s*(?:{_metal}(?:\s*[/–-]\s*|\s+))+{_metal}\s+(?:mon|di|tri|tetra)?oxides?\s*", re.I
    )
    _slash_oxide = re.compile(
        rf"\s*(?:(?:{_metal}|silicon|cerium)\s*/\s*)+(?:{_metal}|silicon|cerium)"
        r"\s+(?:mon|di|tri|tetra)?oxides?\s*",re.I
    )
    _hydroxide = re.compile(rf"\s*{_metal}(?:\s*\([IVX]+\))?\s+(?:mon|di|tri|tetra)?hydroxide\s*",re.I)
    _oxidation = re.compile(r"\(([IVX]+)\)",re.I)
    _compound_preparation = re.compile(r"\b(?:extract|filtrate|ferment|preparation)\s*$",re.I)
    _mixed_components = re.compile(
        rf"\s*(?:{_metal}\s*/\s*)+(?:{_metal}|silicon)\s*/\s*"
        r"(?:(?:fluoride|chloride|hydroxide|oxide|silicate|carbonate)\s*/\s*)*"
        r"(?:fluoride|chloride|hydroxide|oxide|silicate|carbonate)\s*",re.I
    )
    _salt = re.compile(
        rf"^\s*{_metal}(?:\s*\([IVX]+\))?\s+(?:fluoride|chloride|bromide|iodide|carbonate|"
        r"bicarbonate|phosphate|sulfate|sulphate|nitrate|silicate)(?=\s*$|\s+(?:(?:hemi|mono|di|tri|tetra|penta|hexa|hepta|octa|nona|deca)?hydrate|anhydrous)\s*$)",
        re.I,
    )
    _hydrate = re.compile(r"\b(?:(?:hemi|mono|di|tri|tetra|penta|hexa|hepta|octa|nona|deca)?hydrate|hydrated|anhydrous)\b", re.I)
    _basic_salt = re.compile(
        rf"\s*{_metal}\s+(?:carbonate|chloride|phosphate|sulfate|sulphate)\s+hydroxide\s*", re.I
    )
    _complex = re.compile(rf"\b{_metal}\s+complex\s*$", re.I)
    _form = re.compile(r"\b(?:nano(?:particulate)?|microni[sz]ed|fumed|precipitated|rutile|anatase)\b", re.I)
    _clay_definition = re.compile(r"^(?:(?:a|an)\s+)?clay mineral\b", re.I)

    def interpret(self, item):
        name = item.designation.original_value
        assertions = []
        mixed_oxide = self._mixed_oxide.fullmatch(name) or self._slash_oxide.fullmatch(name)
        basic_salt = self._basic_salt.fullmatch(name)
        hydroxide = self._hydroxide.fullmatch(name)
        definition = item.source_definition
        surface_treated = definition and re.search(r"\bsurface[- ]treated with\b",definition.original_value,re.I)
        if mixed := self._mixed_components.fullmatch(name):
            assertions.append(_assert(item,"reported_inorganic_mixed_designation",mixed.group().strip(),
                                      "SLASH_SEPARATED_INORGANIC_COMPONENT_DESIGNATION"))
        if mixed_oxide and not surface_treated:
            convention = ("SLASH_SEPARATED_METAL_OXIDE" if "/" in name else
                          "HYPHENATED_MULTIMETAL_OXIDE" if "-" in name or "–" in name else "NAMED_MULTIMETAL_OXIDE")
            assertions.append(_assert(item, "reported_inorganic_multimetal_oxide", mixed_oxide.group().strip(),
                                      convention))
        if basic_salt:
            assertions.append(_assert(item, "reported_inorganic_salt_name", basic_salt.group().strip(),
                                      "MULTI_ANION_INORGANIC_SALT_NAME"))
        if hydroxide:
            assertions.append(_assert(item,"reported_hydroxide_name",hydroxide.group().strip(),"METAL_HYDROXIDE_NAME"))
        for pattern, predicate, convention in (
            (self._mineral, "reported_mineral_name", "MINERAL_NAME"),
            (self._oxide, "reported_oxide_name", "INORGANIC_OXIDE_NAME"),
            (self._salt, "reported_inorganic_salt_name", "INORGANIC_SALT_NAME"),
            (self._hydrate, "reported_hydration_qualifier", "HYDRATION_QUALIFIER"),
            (self._complex, "reported_metal_complex_qualifier", "METAL_COMPLEX_QUALIFIER"),
        ):
            if pattern is self._oxide and (mixed_oxide or "/" in name):
                continue
            if pattern in (self._mineral,self._oxide) and (self._compound_preparation.search(name) or surface_treated):
                continue
            match = pattern.search(name)
            if pattern is self._oxide and not match:
                match = self._additional_oxide.search(name)
            if match:
                assertions.append(_assert(item, predicate, match.group().strip(), convention))
        if not assertions and definition and re.fullmatch(r"[A-Za-z-]+",name.strip()):
            text = definition.original_value.strip()
            prefix = name.strip()+" is "
            if text.casefold().startswith(prefix.casefold()):
                text = text[len(prefix):]
            if self._clay_definition.match(text):
                assertions.append(_assert(item,"reported_mineral_name",name.strip(),"REPORTED_CLAY_MINERAL_DEFINITION",
                                          role=EvidenceRole.SUPPORTING,evidence=definition))
        if assertions:
            for a in tuple(assertions):
                if a.predicate in {"reported_oxide_name","reported_hydroxide_name","reported_inorganic_salt_name"}:
                    if oxidation := self._oxidation.search(a.value):
                        assertions.append(_assert(item,"reported_oxidation_state",oxidation[1].upper(),
                                                  "EXPLICIT_OXIDATION_NUMERAL",category=Category.NOMENCLATURE))
            if form := self._form.search(name):
                assertions.append(_assert(item, "reported_inorganic_material_form", form.group(), "MATERIAL_FORM_QUALIFIER"))
            return ModuleResult(
                "inorganic_mineral", State.PARTIAL, tuple(a.method for a in assertions), tuple(assertions),
                whole_referent_graph_unestablished=bool(mixed_oxide or basic_salt or hydroxide) or any(
                    a.predicate in ("reported_mineral_name", "reported_oxide_name","reported_inorganic_mixed_designation",
                                    "reported_metal_complex_qualifier", "reported_inorganic_material_form")
                    or a.predicate=="reported_inorganic_salt_name" and "silicate" in a.value.casefold()
                    for a in assertions
                ),
            )
        return None


class Botanical:
    # Match source spelling. The binomial-looking text does not verify a taxon.
    _parts = {
        "leaf": "0025034", "leaves": "0025034", "root": "0009005", "roots": "0009005",
        "flower": "0009046", "flowers": "0009046", "stem": "0009047", "stems": "0009047",
        "seed": "0009010", "seeds": "0009010", "fruit": "0009001", "fruits": "0009001",
    }
    _part = r"(?:stem bark|root bark|whole plant|leaves|(?:leaf|root|flower|stem|seed|fruit|bark|peel|herb|bulb|wood|rhizome|bud|shoot|kernel|hull|sprout)s?)"
    _botanical = re.compile(
        r"(?P<taxon>[A-Za-z][A-Za-z-]+\s+[A-Za-z][A-Za-z-]+)"
        r"(?:\s*\([^)]+\))?\s+"
        rf"(?:(?P<parts>{_part}(?:\s*/\s*{_part})*)\s+)?"
        r"(?P<preparation>oil|juice|extract|distillate|water|powder|wax)", re.I
    )
    _trinomial = re.compile(
        r"(?P<taxon>[A-Za-z][A-Za-z-]+\s+[A-Za-z][A-Za-z-]+\s+(?:(?P<rank>subsp\.|var\.|f\.)\s+)?(?P<epithet>[A-Za-z][A-Za-z-]+))\s+"
        rf"(?P<parts>{_part})\s+(?P<preparation>oil|juice|extract|distillate|water|powder|wax)", re.I
    )
    _hybrid = re.compile(
        rf"(?P<taxon>[A-Za-z-]+\s+[A-Za-z-]+/[A-Za-z-]+)\s+(?P<parts>{_part})\s+"
        r"(?P<preparation>extract|juice|oil|water|powder)",re.I
    )
    _vesicles = re.compile(
        rf"(?P<taxon>[A-Za-z-]+\s+[A-Za-z-]+)\s+(?P<parts>{_part})\s+juice\s+(?P<preparation>vesicles)",re.I
    )
    _gum_water = re.compile(r"(?P<taxon>[A-Za-z-]+\s+[A-Za-z-]+)\s+(?P<parts>gum)\s+(?P<preparation>water)",re.I)
    _taxon_series = re.compile(
        rf"(?P<taxon>[A-Za-z-]+\s+(?P<epithets>[A-Za-z-]+(?:/[A-Za-z-]+){{2,}}))\s+"
        rf"(?P<parts>{_part})\s+(?P<preparation>extract|juice|oil|water|powder)",re.I
    )
    _part_only = re.compile(rf"(?P<taxon>[A-Za-z-]+\s+[A-Za-z-]+)\s+(?P<parts>hull|kernel|sprout|leaf|flower|fruit|seed|root)",re.I)
    _whole_plant = re.compile(r"\b(?:extract of|obtained from)\s+(?:the\s+)?(?P<part>whole plant)\b",re.I)
    _definition_part = re.compile(
        rf"\b(?:extract|juice|oil|powder)\s+(?:(?:obtained|derived|expressed)\s+)?(?:of|from)\s+(?:the\s+)?(?P<part>(?>{_part}))\b(?!\s*(?:/|and\b|or\b))",re.I
    )
    _plant_evidence = re.compile(r"\b(?:plants?|botanical|trees?|[A-Za-z]+aceae)\b", re.I)
    _non_taxon = re.compile(r"\b(?:hydroly[sz]ed|hydrogenated|denatured|sodium|calcium|acid|coral|protein|synthetic)\b", re.I)
    _nonplant_source = re.compile(
        r"\b(?:is|extract of|derived from|obtained from)\s+(?:(?:a|an|the)\s+)?"
        r"(?:bacterium|bacteria|fungus|yeast|alga|coral)\b", re.I
    )

    def interpret(self, item):
        name = item.designation.original_value.strip()
        source = item.source_definition
        if source and self._nonplant_source.search(source.original_value):
            return None
        match = self._botanical.fullmatch(name)
        preparation = None
        grounded = False
        taxon_ambiguous = False
        rank = None
        part_only = False
        if not match and source:
            for pattern, definition, preparation_value in (
                (self._hybrid,r"\bhybrid\b",None),
                (self._vesicles,r"\bvesicles isolated from (?:the )?juice\b","vesicles"),
                (self._gum_water,_AQUEOUS_STEAM_DISTILLATE.pattern,"steam distillate"),
            ):
                candidate = pattern.fullmatch(name)
                if candidate and re.search(definition,source.original_value,re.I):
                    match,preparation,grounded = candidate,preparation_value,True
                    break
        if not match and source:
            candidate = self._trinomial.fullmatch(name)
            if (candidate and not re.fullmatch(self._part,candidate["epithet"],re.I)
                    and candidate["taxon"].casefold() in source.original_value.casefold()):
                match = candidate
                rank = candidate["rank"]
        if not match and source:
            candidate = self._taxon_series.fullmatch(name)
            if candidate and all(re.search(rf"\b{re.escape(term)}\b",source.original_value,re.I)
                                 for term in candidate["epithets"].split("/")):
                match,grounded,taxon_ambiguous = candidate,True,True
        if not match and source:
            candidate = self._part_only.fullmatch(name)
            if candidate:
                source_text = source.original_value
                exact_part = self._plant_evidence.search(source_text) and re.search(
                    rf"\b{re.escape(candidate['parts'])}\b",source_text,re.I)
                reported_covering = (candidate["parts"].casefold()=="hull" and
                    candidate["taxon"].casefold() in source_text.casefold() and
                    re.search(r"\bouter covering of\b",source_text,re.I))
                if exact_part or reported_covering:
                    match,part_only = candidate,True
        if not match or self._non_taxon.search(match["taxon"]):
            return None
        supported = source and self._plant_evidence.search(source.original_value)
        if not match["parts"] and not supported:
            return None
        convention = ("SOURCE_DEFINITION_SUPPORTED_BOTANICAL_PREPARATION" if grounded else
                      "BOTANICAL_PART_GRAMMAR" if match["parts"] else "BINOMIAL_LIKE_NAME_WITH_REPORTED_PLANT_SOURCE")
        assertions,issues = [],[]
        if taxon_ambiguous:
            issues.append(Issue("MULTIPLE_REPORTED_BOTANICAL_SOURCES",(item.designation,source),
                                affected_slots=("botanical.taxon",)))
        else:
            assertions.append(_assert(item,"reported_taxon_text",match["taxon"],convention,role=EvidenceRole.CANDIDATE_ONLY,
                                      slot="botanical.taxon"))
        if rank:
            assertions.append(_assert(item,"reported_taxon_rank",rank,convention,role=EvidenceRole.CANDIDATE_ONLY,
                                      depends_on=("botanical.taxon",)))
        if not part_only:
            assertions.append(_assert(item,"reported_botanical_preparation",preparation or match["preparation"],convention,
                                      evidence=source if grounded else None,
                                      slot="preparation.final_form" if _disputed_form(item) else None))
        if supported and not match["parts"]:
            assertions.append(_assert(item, "reported_plant_source_context", "PLANT_SOURCE_WORDING", convention,
                                      role=EvidenceRole.SUPPORTING, evidence=source))
        part_text = match["parts"]
        definition_part = self._whole_plant.search(source.original_value) if source and not part_text else None
        parts = re.split(r"\s*/\s*",part_text or (definition_part["part"] if definition_part else ""))
        part_claims = [(p,source if definition_part else None) for p in parts if p]
        declared = self._definition_part.search(source.original_value) if source and part_text and len(parts)==1 else None
        conflict_part = False
        if declared:
            a,b = parts[0].casefold(),declared["part"].casefold()
            equivalent = (a.removesuffix("s")==b.removesuffix("s")
                          or self._parts.get(a) is not None and self._parts.get(a)==self._parts.get(b))
            compatible = {a,b} in ({"bark","stem bark"},{"bark","root bark"})
            if not equivalent and not compatible:
                part_claims.append((declared["part"],source))
                conflict_part = True
        anatomy_slot = "botanical.anatomy" if conflict_part else None
        for part,evidence in part_claims:
            assertions.append(_assert(item, "reported_plant_part", part, convention,
                                      evidence=evidence,slot=anatomy_slot))
            if code := self._parts.get(part.lower()):
                assertions.append(_assert(item, "source_anatomical_structure",
                                          f"http://purl.obolibrary.org/obo/PO_{code}",
                                          convention, role=EvidenceRole.SUPPORTING,evidence=evidence,
                                          depends_on=(anatomy_slot,) if anatomy_slot else ()))
        return ModuleResult("botanical", State.PARTIAL, (convention,), tuple(assertions),tuple(issues),
                            whole_referent_graph_unestablished=True)


class BiologicalBiotechnological:
    _protein = re.compile(r"^(?:hydroly[sz]ed\s+)?(?P<source>[A-Za-z-]+)\s+protein$", re.I)
    _category = re.compile(r"\b(?:proteins?|(?:(?:oligo|poly|di|tri|tetra|penta|hexa|hepta|octa|nona|deca)?peptides?)(?:-\d+)?"
                           r"|enzyme|ferment|fermentation|hydroly[sz]ate|lysate)\b", re.I)
    _culture_media = re.compile(r"\b(?:growth media removed from cultures|conditioned (?:media|medium) from cultures)\b",re.I)

    def interpret(self, item):
        name = item.designation.original_value.strip()
        matches = list(self._category.finditer(name))
        convention = "BIOLOGICAL_PREPARATION_OR_BIOMOLECULE_QUALIFIER"
        assertions = [_assert(item, "reported_biological_category", match.group(), convention) for match in matches]
        definition = item.source_definition
        if definition and re.search(r"\bconditioned (?:media|medium)\b",name,re.I) and self._culture_media.search(definition.original_value):
            assertions.append(_assert(item,"reported_biological_category","conditioned media","SOURCE_CULTURE_MEDIUM_DEFINITION",
                                      role=EvidenceRole.SUPPORTING,evidence=definition))
        if not assertions:
            return None
        if protein := self._protein.fullmatch(name):
            assertions.append(_assert(item, "reported_biological_source_text", protein["source"], convention,
                                      role=EvidenceRole.CANDIDATE_ONLY))
        return ModuleResult("biological_biotechnological", State.PARTIAL, (convention,), tuple(assertions),
                            whole_referent_graph_unestablished=True)


class PolymerSilicone:
    _polymer = re.compile(
        r"\b(?:polymer|crosspolymer|copolymer|terpolymer|silicone|dimethicone|polysiloxane|polyurethane|"
        r"polyethylene glycol|polypropylene glycol|polyethylene|polypropylene|nylon|"
        r"polyquaternium|polyglyceryl|polyglycerin)\b", re.I
    )
    _grade = re.compile(r"\b(?:PEG/PPG[- ]\d+/\d+|(?:PEG|PPG|NYLON|POLYQUATERNIUM|POLYGLYCERYL|POLYGLYCERIN)[- ]\d+)\b", re.I)
    _polyurethane_number = re.compile(r"\s*POLYURETHANE-\d+\s*",re.I)
    _segments = re.compile(r"(?P<segments>[A-Za-z][A-Za-z0-9 -]*(?:/[A-Za-z][A-Za-z0-9 -]*)+)\s+(?:co|cross|ter)polymer", re.I)

    def interpret(self, item):
        name = item.designation.original_value
        assertions = []
        for category in self._polymer.finditer(name):
            assertions.append(_assert(item, "reported_polymer_category", category.group(), "POLYMER_QUALIFIER"))
        for grade in self._grade.finditer(name):
            polyether = grade.group().upper().startswith(("PEG", "PPG"))
            predicate = "reported_polyether_grade" if polyether else "reported_polymer_designation_number"
            convention = "PEG_PPG_GRADE_NOTATION" if polyether else "NUMBERED_POLYMER_DESIGNATION"
            assertions.append(_assert(item, predicate, grade.group(), convention, category=Category.NOMENCLATURE))
        if numbered := self._polyurethane_number.fullmatch(name):
            assertions.append(_assert(item,"reported_polymer_designation_number",numbered.group().strip(),
                                      "NUMBERED_POLYMER_DESIGNATION",category=Category.NOMENCLATURE))
        if segments := self._segments.fullmatch(name.strip()):
            assertions.append(_assert(item, "reported_polymer_name_segments", segments["segments"],
                                      "SLASH_SEPARATED_POLYMER_NAME", category=Category.NOMENCLATURE,
                                      role=EvidenceRole.CANDIDATE_ONLY))
        if not assertions:
            return None
        return ModuleResult("polymer_silicone", State.PARTIAL, tuple(a.method for a in assertions), tuple(assertions),
                            whole_referent_graph_unestablished=True)


class LipidSurfactant:
    _qualifier = re.compile(
        r"\b(?:glycerides?|triglycerides?|diglycerides?|monoglycerides?|fatty\s+(?:acid|alcohol)s?|"
        r"(?:caprylic|capric|lauric|myristic|palmitic|stearic|isostearic|oleic|linoleic)\s+acid|"
        r"(?:cetyl|stearyl|cetearyl|oleyl)\s+alcohol|ethoxylated|propoxylated|"
        r"(?:laureth|ceteareth|steareth|ceteth|oleth|pareth|trideceth)(?:-\d+)?|"
        r"(?:laur|stear|ole|linole|isostear|palmit|myrist|capr|capryl|isodecano|oliv)ate|"
        r"(?:lauryl|myristyl|stearyl)\s+sul(?:f|ph)ate)\b", re.I
    )
    _ethoxylate_grade = re.compile(r"\b(?:sorbeth|glycereth|alketh|isodeceth)-\d+\b",re.I)
    _ether_definition = re.compile(r"\b(?:is (?:the |an? )?polyethylene glycol ether of|ethoxylated\s*\()",re.I)
    _standalone_ethoxylate = re.compile(r"[A-Z]+(?:ETH|OXYNOL)-(?P<grade>\d+)",re.I)
    _reported_eo = re.compile(r"\bethoxylated\s*(?:\(\s*|,\s*)(\d+)\s+mol\s+EO\b",re.I)
    _reported_phenol_grade = re.compile(
        r"\bis the ethoxylated alkyl phenol\b[^.]{0,150}\bn has an average value of (\d+)\b",re.I
    )
    _glycolipid_definition = re.compile(r"\b(?:is|are) (?:an? |the )?(?P<family>glycolipids?)\b",re.I)

    def interpret(self, item):
        matches = list(self._qualifier.finditer(item.designation.original_value))
        convention = "LIPID_OR_SURFACTANT_NAMING_QUALIFIER"
        assertions = [_assert(item, "reported_lipid_surfactant_qualifier", match.group(), convention,
                               category=Category.NOMENCLATURE) for match in matches]
        distribution = any(re.fullmatch(
            r"(?:ethoxylated|propoxylated|(?:laureth|ceteareth|steareth|ceteth|oleth|pareth|trideceth)-\d+|"
            r"(?:mono|di|tri)?glycerides|isostearate|isostearic acid)", m.group(), re.I
        ) for m in matches)
        source = item.source_definition
        if source and self._ether_definition.search(source.original_value):
            if grade := self._ethoxylate_grade.search(item.designation.original_value):
                assertions.append(_assert(item,"reported_lipid_surfactant_qualifier",grade.group(),
                                          "SOURCE_SUPPORTED_ETHOXYLATE_GRADE",category=Category.NOMENCLATURE))
                distribution = True
        if source and not distribution:
            grade = self._standalone_ethoxylate.fullmatch(item.designation.original_value)
            reported = self._reported_eo.search(source.original_value) or self._reported_phenol_grade.search(source.original_value)
            if grade and reported and grade["grade"]==reported[1]:
                assertions.append(_assert(item,"reported_lipid_surfactant_qualifier",grade.group(),
                                          "SOURCE_SUPPORTED_ETHOXYLATE_GRADE",category=Category.NOMENCLATURE))
                distribution = True
        if source and (family := self._glycolipid_definition.search(source.original_value)):
            assertions.append(_assert(item,"reported_lipid_surfactant_qualifier",family["family"],
                                      "REPORTED_GLYCOLIPID_FAMILY",evidence=source,role=EvidenceRole.SUPPORTING))
            distribution = True
        if not assertions:
            return None
        return ModuleResult("lipid_surfactant", State.PARTIAL,tuple(dict.fromkeys(a.method for a in assertions)),tuple(assertions),
                            whole_referent_graph_unestablished=distribution)


class Colorant:
    _ci = re.compile(r"C\.?\s*I\.?\s*(?P<number>[0-9]{5,6}(?::[0-9]+)?)", re.I)
    _ci_generic = re.compile(
        r"(?:C\.?\s*I\.?\s*)?(?P<designation>"
        r"(?:acid|basic|direct|disperse|food|mordant|pigment|reactive|solvent|sulfur|vat)\s+"
        r"(?:black|blue|brown|green|grey|gray|orange|red|violet|white|yellow)\s+[0-9]+(?::[0-9]+)?)"
        r"(?:\s+(?P<lake>(?:aluminium|aluminum|barium|calcium|zirconium)\s+lake|lake))?",
        re.I,
    )
    _form = re.compile(r"\b(?:pigment|dye|colourant|colorant|lake)\b", re.I)
    _hc = re.compile(r"HC\s+(?:BLACK|BLUE|BROWN|GREEN|ORANGE|RED|VIOLET|YELLOW)\s+(?:NO\.?\s*)?\d+",re.I)

    def interpret(self, item):
        name = item.designation.original_value.strip()
        assertions = []
        if match := self._ci.fullmatch(name):
            convention = "COLOUR_INDEX_NUMBER_SYNTAX"
            assertion = _assert(item, "ColourIndex", match["number"], convention,
                                category=Category.IDENTIFIER, role=EvidenceRole.CANDIDATE_ONLY)
        elif match := self._ci_generic.fullmatch(name):
            convention = "COLOUR_INDEX_GENERIC_NAME_SYNTAX"
            assertion = _assert(item, "ColourIndexGenericName", match["designation"], convention,
                                category=Category.IDENTIFIER, role=EvidenceRole.CANDIDATE_ONLY)
            if match["lake"]:
                assertions.append(_assert(item, "reported_colorant_qualifier", match["lake"], "COLORANT_FORM_QUALIFIER"))
        elif match := self._hc.fullmatch(name):
            convention = "HC_NUMBERED_COLORANT_DESIGNATION"
            assertion = _assert(item,"HCColorantDesignation",match.group(),convention,
                                category=Category.IDENTIFIER,role=EvidenceRole.CANDIDATE_ONLY)
        elif match := self._form.search(name):
            convention = "COLORANT_FORM_QUALIFIER"
            assertion = _assert(item, "reported_colorant_qualifier", match.group(), convention)
        else:
            return None
        assertions.insert(0, assertion)
        return ModuleResult("colorant", State.PARTIAL, tuple(a.method for a in assertions), tuple(assertions),
                            whole_referent_graph_unestablished=True)


class PreparationMixture:
    _qualifier = re.compile(
        r"\b(?:denat(?:ured)?\.?|hydroly[sz]ed|hydrogenated|blend|mixture|juice|extract|distillate|preparation|filtrate|"
        r"(?:seed|leaf|root|flower|stem|essential|vegetable)\s+oil|(?:oil|wax)(?=\s*$))(?=\s|$|[,;)])",
        re.I,
    )
    _source_mixture = re.compile(r"\bis (?:a|the) (?P<qualifier>(?:complex )?mixture|blend) of\b", re.I)
    _special_denatured = re.compile(r"\s*SD ALCOHOL(?: \d+[A-Z]?(?:-[A-Z])?)?\s*",re.I)

    def interpret(self, item):
        name = item.designation.original_value
        matches = self._qualifier.finditer(name)
        convention = "EXPLICIT_PREPARATION_OR_MIXTURE_QUALIFIER"
        assertions = []
        disputed = _disputed_form(item)
        for match in matches:
            value = match.group()
            if value.casefold().endswith(" oil") and name[match.end():].strip():
                assertions.append(_assert(item, "reported_preparation_source_phrase", value,
                                          "NONTERMINAL_OIL_PHRASE", role=EvidenceRole.SUPPORTING))
            else:
                final = disputed and _FINAL_FORM.fullmatch(value) and not name[match.end():].strip()
                assertions.append(_assert(item, "reported_preparation_qualifier", value, convention,
                                          slot="preparation.final_form" if final else None))
        definition = item.source_definition
        if disputed:
            assertions.append(_assert(item,"reported_source_preparation",disputed,"EXPLICIT_SOURCE_PREPARATION_TYPE",
                                      role=EvidenceRole.SUPPORTING,evidence=definition,slot="preparation.final_form"))
        if definition and (match := self._source_mixture.search(definition.original_value)):
            assertions.append(_assert(item, "reported_source_preparation", match["qualifier"], "REPORTED_SOURCE_MIXTURE",
                                      role=EvidenceRole.SUPPORTING, evidence=definition))
        if definition and self._special_denatured.fullmatch(name) and re.search(r"\bdenatured with\b",definition.original_value,re.I):
            assertions.append(_assert(item,"reported_source_preparation","denatured alcohol","SOURCE_DENATURATION_DEFINITION",
                                      role=EvidenceRole.SUPPORTING,evidence=definition))
        if definition and re.search(r"\bwater\s*$",name,re.I) and _AQUEOUS_STEAM_DISTILLATE.search(definition.original_value):
            assertions.append(_assert(item,"reported_source_preparation","steam distillate","SOURCE_AQUEOUS_DISTILLATE_DEFINITION",
                                      role=EvidenceRole.SUPPORTING,evidence=definition))
        if definition:
            for pattern, process in (
                (r"\b(?:obtained|produced) by (?:the )?(?:spontaneous )?fermentation\b","fermentation"),
                (r"\b(?:is|are) (?:a |the )?filtrates? of\b","filtration"),
                (r"\b(?:is|are) (?:an? |the )?hydroly[sz]ates? of\b|\b(?:obtained|produced) by (?:the )?hydrolysis\b","hydrolysis"),
                (r"\bsurface[- ]treated with\b","surface treatment"),
            ):
                if re.search(pattern,definition.original_value,re.I):
                    assertions.append(_assert(item,"reported_preparation_process",process,"EXPLICIT_SOURCE_PROCESS",
                                              role=EvidenceRole.SUPPORTING,evidence=definition))
        if not assertions:
            return None
        return ModuleResult("preparation_mixture", State.PARTIAL, tuple(dict.fromkeys(a.method for a in assertions)),
                            tuple(assertions),
                            whole_referent_graph_unestablished=True)


class GenericIngredient:
    def interpret(self, item):
        return ModuleResult("generic_ingredient", State.UNINTERPRETED)
