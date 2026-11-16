"""Small read-only adapters for existing source and canonical-link contracts."""

import json

from canonical_registry.nomenclature_interpretation.contracts import Evidence, ReportedIdentifier
from canonical_registry.nomenclature_interpretation.cosing_preview_adapter import adapt_cosing_preview

from .contracts import ChemicalTarget, Ingredient, RegistryType


def from_cosing(row, aliases, scope, interpreter, **qualification) -> Ingredient:
    """Build a comparison input without promoting reported fields to reviewed evidence."""
    item = adapt_cosing_preview(row, aliases)
    reference = item.designation.source_reference
    ids = list(item.identifiers)
    for field, scheme in (("cas_nos", "CAS"), ("ec_nos", "EC")):
        values = row.get(field)
        for index, value in enumerate((json.loads(values) if isinstance(values, str) else values) or ()):
            if isinstance(value, str) and value.strip():
                ids.append(ReportedIdentifier(scheme, Evidence(value, f"{field}[{index}]", reference)))
    search_aliases = tuple(Evidence(alias["alias"], alias["alias_type"],
                                    f"mse_dwd.dwd_mse_cosmetics_inci_aliases:{alias['inci_alias_id']}",
                                    alias["source"])
                           for alias in aliases if alias["alias_type"] in
                           {"INCI", "INCI_NAME", "PREFERRED_NAME", "CHEMICAL_NAME", "SYNONYM"})
    return Ingredient(reference, row["inci"], scope, interpretation=interpreter.interpret(item),
                      reported_identifiers=tuple(ids), search_aliases=search_aliases, **qualification)


def verified_cosmetics_target(record, registry, snapshot, exists) -> ChemicalTarget | None:
    """Project a resolved CosmeticsIngredientConcept mapping after a snapshot-bound existence check.

    The upstream producer must have applied the established chemical admission/matching
    rules. This function neither admits a chemical nor upgrades a preview or source alias.
    The verifier must check the named registry and immutable snapshot.
    """
    statuses = {"RESOLVED_SUBSTANCE": RegistryType.SUBSTANCE, "RESOLVED_CHEMICAL_CONCEPT": RegistryType.CHEMICAL_CONCEPT}
    status = record["canonical_status"]
    target = record.get("canonical_target")
    if status in {"NOT_EVALUATED", "UNRESOLVED"}:
        if "canonical_target" in record:
            raise ValueError("An unresolved concept cannot have a canonical target")
        return None
    if status not in statuses or not isinstance(target, dict) or target.get("registry_type") != statuses[status]:
        raise ValueError("Canonical status and target type disagree")
    identity = target.get("id")
    if not isinstance(identity, str) or not identity.strip() or not exists(registry, snapshot, statuses[status], identity):
        raise ValueError("Canonical target does not exist in the supplied snapshot")
    reference = f"{record['source_reference']}#{record['ingredient_concept_id']}"
    return ChemicalTarget(record["source_reference"], statuses[status], registry, snapshot, identity,
                          Evidence(identity, "validated_canonical_target", reference))
