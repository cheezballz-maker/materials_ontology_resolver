"""Acquire and qualify provider molecular records using the shared evidence gate."""

import argparse
from dataclasses import asdict, replace
from pathlib import Path
import re
from time import sleep
from urllib.parse import urlencode

from canonical_registry.authoritative_lookup.lookup import AuthorityRecord, _attach, normalize, _same_graph
from canonical_registry.authoritative_lookup.sources import read, write
from canonical_registry.cosing_pilot.stage_b_handoff import Trace
from canonical_registry.chemistry import describe
from canonical_registry.identity_sufficiency.contract import Claim, digest, structure_signature
from .cohort import DATA
from .evaluation.authority_access import capture, CHEBI, PUBCHEM, PROPERTIES

ROOT = DATA / "v3"
KEY = re.compile(r"[A-Z]{14}-[A-Z]{10}-[A-Z]")


def queue(root=ROOT, *, fresh_limit=None, budget=115):
    rows = read(root / "fresh.json")[:fresh_limit]
    controls = read(DATA.parent.parent / "authoritative_lookup/data/cohort.json")
    selected = {}
    for row, old in [(r, True) for r in controls] + [(r, False) for r in rows]:
        if row["group"] == "development" and row["parent"]["inci"] not in {
            "WATER", "AQUA", "ALCOHOL", "GLYCERIN", "ACETONE", "HYDROGEN PEROXIDE", "CITRIC ACID", "SODIUM CHLORIDE",
            "GLUTAMIC ACID", "MAGNESIUM SULFATE", "ALCOHOL DENAT.", "CAFFEINE", "BENZOIC ACID",
        }:
            continue
        if old and row["group"] != "development":
            continue
        if row["old_status"] != "NEEDS_MORE_EVIDENCE":
            continue
        keys = row["queries"]["INCHIKEY"]
        if len(keys) == 1 and KEY.fullmatch(keys[0]):
            selected.setdefault(keys[0], row["concept_id"])
    result = dict(list(selected.items())[:budget])
    write(root / "provider_queue.json", result)
    print(len(result))


def acquire(provider, root=ROOT):
    path = root / (provider + "_capture.json")
    records = read(path) if path.exists() else {}

    def fetch(url):
        if url not in records:
            records[url] = capture(url)
            write(path, records)
            sleep(.35)
        return records[url].get("data", {})

    for key in read(root / "provider_queue.json"):
        if not KEY.fullmatch(key):
            raise ValueError("Expected a public full InChIKey")
        if provider == "pubchem":
            fetch(PUBCHEM + "inchikey/" + key + PROPERTIES)
            continue
        data = fetch(CHEBI + "es_search/?" + urlencode({"term": key, "size": 4, "page": 1}))
        for hit in data.get("results", [])[:4]:
            accession = hit.get("_source", {}).get("chebi_accession", "")
            if re.fullmatch(r"CHEBI:[0-9]+", accession):
                fetch(CHEBI + "compound/" + accession + "/")
    print(provider, len(records))


def records(root=ROOT):
    for provider in ("pubchem", "chebi"):
        for packet in read(root / (provider + "_capture.json")).values():
            if packet["status"] != "JSON_CAPTURED":
                continue
            data = packet["data"]
            if provider == "pubchem":
                for row in data.get("PropertyTable", {}).get("Properties", []):
                    yield provider, packet, row
            elif data.get("chebi_accession"):
                yield provider, packet, data


def adapt(provider, packet, row):
    if provider == "pubchem":
        if not isinstance(row.get("CID"), int):
            raise ValueError("PUBCHEM_CID_REQUIRED")
        entity = "CID:" + str(row["CID"])
        name = row.get("IUPACName")
        smiles, inchi, key = (row.get(field) for field in ("SMILES", "InChI", "InChIKey"))
        authority, locator = "PubChem", "Compound computed IUPACName and standardized molecular structure"
    elif provider == "chebi":
        structural = row.get("default_structure") or {}
        if (row.get("is_released") is not True or row.get("stars") != 3 or not row.get("definition")
            or structural.get("is_r_group") is not False or not re.fullmatch(r"CHEBI:[0-9]+", row["chebi_accession"])):
            raise ValueError("CHEBI_DEFINED_DISCRETE_RELEASE_REQUIRED")
        entity = row["chebi_accession"]
        name = row.get("ascii_name")
        smiles, inchi, key = (structural.get(field) for field in ("smiles", "standard_inchi", "standard_inchi_key"))
        authority, locator = "ChEBI", "Curated preferred name, definition and default structure"
    else:
        raise ValueError("UNSUPPORTED_AUTHORITY")
    if not name or not smiles or "*" in smiles or not inchi or not key:
        raise ValueError("AUTHORITY_GRAPH_OR_NAME_MISSING")
    graph = describe(smiles)
    if (graph["inchi"], graph["inchikey"]) != (inchi, key):
        raise ValueError("AUTHORITY_STRUCTURE_DESCRIPTOR_DISAGREES")
    if graph["components"] != 1:
        raise ValueError("AUTHORITY_COMPLETE_COMPONENT_ROLE_UNESTABLISHED")
    provenance = {field: packet[field] for field in ("sha256", "retrieved_at", "url")}
    provenance.update(record_version=row.get("modified_on"), lineage="UPSTREAM_INDEPENDENCE_UNESTABLISHED",
                      definition=row.get("definition"), database_links=row.get("database_accessions"),
                      authority_name_role="COMPUTED_IUPAC_NAME" if provider == "pubchem" else "CURATED_PREFERRED_NAME")
    return AuthorityRecord(entity, authority, "SMILES", smiles, key, (name,), {}, packet["url"], locator, provenance), graph


def binding(source, authority, graph, independent_name_graph=None):
    e = source.evidence
    if e.holds or e.material_scope != "UNESTABLISHED" or any(len(v) > 1 for v in source.identifiers.values()):
        return "SOURCE_SCOPE_OR_IDENTIFIERS_UNRESOLVED"
    if not source.preferred_name_graph_retained:
        return "NO_DETERMINISTIC_PREFERRED_NAME_GRAPH"
    if (normalize(e.designation) != normalize(authority.names[0]) and
        independent_name_graph != structure_signature(graph)):
        return "AUTHORITY_NAME_IS_NOT_SOURCE_DESIGNATION"
    signature = structure_signature(graph)
    if not source.graph_signatures or any(g != signature for g in source.graph_signatures) or any(
        c.kind == "INCHIKEY" and c.value != graph["inchikey"] for c in e.claims
    ):
        return "SOURCE_GRAPH_FORM_DISAGREEMENT"
    return "QUALIFIED_PREFERRED_NAME_AND_GRAPH"


def retained_source_input(row, source, review=None):
    """Only a retained preferred-designation reading can bind an external name."""
    trace = Trace(row["attributes"], row["summary"], row["trace"])
    readings = {a["value"] for a in trace.interpretation.get("assertions", [])
                if a["predicate"] == "molecular_name_reading"}
    retained = any(a["method"] == "OPSIN_THEN_STRICT_RDKIT" for a in trace.graphs)
    evidence = source.evidence
    if review:
        reason = review["reason"]
        if (review["revision"], review["designation"]) != (evidence.source_revision, evidence.designation):
            reason = "REVIEW_SCOPE_RECEIPT_STALE"
        claim = Claim("source-review:" + digest(review), "DEFINITION", review["finding"], "SCOPE_UNESTABLISHED",
                      evidence.referent, review["authority"], (), review["url"], review["locator"], digest(review))
        evidence = replace(evidence, claims=(*evidence.claims, claim), holds=(*evidence.holds, reason))
    return replace(source, evidence=evidence, preferred_name_graph_retained=retained and not trace.guard and
                   not trace.withheld and readings == {"ESTABLISHED"})


class MultiAuthority:
    """Compose provider-specific bindings with the existing GSRS lookup."""

    def __init__(self, existing, name_parser=None, *, evidence_root=ROOT):
        self.existing = existing
        self.authorities = existing.authorities
        self.index = {}
        self.names = {}
        self.name_parser = name_parser
        self.parsed_names = {}
        self.rejected = []
        for provider, packet, row in records(evidence_root):
            try:
                record, graph = adapt(provider, packet, row)
            except (ValueError, RuntimeError) as exc:
                self.rejected.append([provider, row.get("CID", row.get("chebi_accession")), str(exc)])
                continue
            self.index.setdefault(record.inchikey, []).append((record, graph))
            self.names.setdefault(normalize(record.names[0]), []).append((record, graph))

    def authority_name_graph(self, source, authority):
        if not (self.name_parser and source.preferred_name_graph_retained and
                authority.authority == "PubChem"):
            return None
        name = authority.names[0]
        if name not in self.parsed_names:
            result = self.name_parser(name)
            signature = None
            if result["status"] == "SUCCESS" and result.get("smiles"):
                try:
                    signature = structure_signature(describe(result["smiles"]))
                except (ValueError, RuntimeError):
                    pass
            self.parsed_names[name] = signature
        return self.parsed_names[name]

    def evaluate(self, source, candidates, total, *, authority_source=False):
        decision, prior, evaluated = self.existing.evaluate(source, candidates, total, authority_source=authority_source)
        if authority_source or total != len(candidates) or decision["eligibility"] not in {"CANDIDATE_READY", "NEEDS_MORE_EVIDENCE"}:
            return decision, prior, evaluated
        accepted = []
        found = {(a.authority, a.entity): (a, g) for key in sorted({s[2] for s in source.graph_signatures})
                 for a, g in self.index.get(key, ())}
        found.update({(a.authority, a.entity): (a, g) for a, g in
                      self.names.get(normalize(source.evidence.designation), ())})
        explicit_conflict = False
        for authority, graph in found.values():
            outcome = binding(source, authority, graph, self.authority_name_graph(source, authority))
            evaluated.append({"authority_entity": authority.entity, "authority": authority.authority,
                              "inchikey": authority.inchikey, "assessment": [outcome]})
            explicit_conflict |= outcome == "SOURCE_GRAPH_FORM_DISAGREEMENT"
            if outcome == "QUALIFIED_PREFERRED_NAME_AND_GRAPH":
                accepted.append((authority, graph))
        if explicit_conflict and (prior or accepted):
            e = replace(source.evidence, holds=("COMPETING_AUTHORITY_STRUCTURAL_FORMS",))
            return self.existing.evaluator.evaluate(e), None, evaluated
        if not accepted:
            return decision, prior, evaluated
        chosen, graph = accepted[0]
        signatures = {structure_signature(g) for _, g in accepted}
        if prior:
            signatures.add(tuple(prior["specificity"][k] for k in ("smiles", "inchi", "inchikey", "fixed_h_inchi")))
        candidate_conflicts = [c["chemical_id"] for c in candidates if any(
            r.startswith(("PREFERRED_NAME:", "REPORTED_ALIAS:NAME:")) for r in c["routes"]) and
            not _same_graph(c, graph)]
        if len(signatures) > 1 or candidate_conflicts:
            e = replace(source.evidence, holds=("COMPETING_AUTHORITY_STRUCTURAL_FORMS",))
            return self.existing.evaluator.evaluate(e), None, evaluated
        supporting = [{"authority": record.authority, "entity": record.entity, "provenance": record.provenance,
                       "signature": structure_signature(g), "authority_name": record.names[0]}
                      for record, g in accepted]
        if prior and decision["eligibility"] == "CANDIDATE_READY":
            prior["cross_provider_support"] = supporting
            prior["receipt_sha256"] = digest({k: v for k, v in prior.items() if k != "receipt_sha256"})
            return decision, prior, evaluated
        e, receipt = _attach(source.evidence, chosen, None, graph, "AUTHORITY_PREFERRED_NAME_AND_SOURCE_GRAPH",
                             {"binding_value": source.evidence.designation, "authority_name": chosen.names[0],
                              "compared_source_graphs": source.graph_signatures}, ["Provider independence unestablished."])
        decision = self.existing.evaluator.evaluate(e)
        receipt["cross_provider_support"] = supporting
        receipt["validation"] = {"eligibility": decision["eligibility"], "reasons": decision["reasons"],
                                 "official_inchi": decision.get("official_validation")}
        receipt["receipt_sha256"] = digest(receipt)
        return decision, receipt, evaluated


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("queue", "pubchem", "chebi"))
    parser.add_argument("--safety-closure", action="store_true")
    options = parser.parse_args()
    root = DATA / "safety_closure" if options.safety_closure else ROOT
    queue(root) if options.operation == "queue" else acquire(options.operation, root)
