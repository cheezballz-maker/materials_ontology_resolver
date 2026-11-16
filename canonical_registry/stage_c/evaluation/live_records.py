"""Translate verified live authority packets into existing lookup inputs."""

from canonical_registry.authoritative_lookup.sources import authority_records, read, write
from canonical_registry.chemistry import describe
from .authority_access import DATA


def live_records(packet):
    providers = {"GSRS": [], "NIST_ECHA_FDA": {"records": []}, "ChEBI": [], "PubChem": []}
    diagnostics = {}
    for name, receipt in packet["records"].items():
        if receipt["status"] != "JSON_CAPTURED":
            diagnostics[name] = receipt["status"]
            continue
        body = receipt["data"]
        capture = {k: receipt[k] for k in ("url", "sha256", "retrieved_at", "http_status")}
        if body.get("approvalID") and body.get("uuid") and body.get("substanceClass"):
            providers["GSRS"].append({"capture": {**capture, "stage_c_live_native": True,
                                                  "record_status": body.get("status"),
                                                  "record_type": body["substanceClass"],
                                                  "relationships": body.get("relationships", [])}, "records": [body]})
        elif name.startswith("pubchem_") and body.get("PropertyTable", {}).get("Properties"):
            providers["PubChem"].append({"capture": capture, "records": body["PropertyTable"]["Properties"]})
        elif name.startswith("chebi_") and body.get("chebi_accession"):
            providers["ChEBI"].append({"capture": capture, "records": [body]})
        elif body.get("IdentifierList"):
            diagnostics[name] = {"candidate_ids": body["IdentifierList"].get("CID", [])}
        elif body.get("InformationList"):
            diagnostics[name] = {"annotation_fields": sorted({key for r in body["InformationList"].get("Information", [])
                                                                for key in r})}
        elif "total" in body:
            diagnostics[name] = {"search_total": body["total"]}
    validated, supplemental, rejected = authority_records(providers)
    seen = {}
    for key, values in validated.items():
        for value in values:
            seen.setdefault(key, {})[(value.entity, value.provenance.get("native_revision"))] = value
    return {key: list(values.values()) for key, values in seen.items()}, supplemental, rejected, diagnostics


def verify_controls(packet, by_unii, supplemental, diagnostics):
    key = describe("CCO")["inchikey"]
    assert any(a.inchikey == key for a in by_unii["3K9958V90M"])
    assert any(a.inchikey == describe("OCC(O)CO")["inchikey"] for a in by_unii["PDC6A3C0OX"])
    assert sum(r["entity"] == "CID:702" and r["inchikey"] == key and
               r["validation"] == "STRICT_STRUCTURE_AGREES" for r in supplemental) >= 2
    assert 702 in diagnostics["pubchem_structure"]["candidate_ids"]
    assert len(diagnostics["pubchem_multiple"]["candidate_ids"]) > 1
    assert "Synonym" in diagnostics["pubchem_synonyms"]["annotation_fields"]
    assert "SID" in diagnostics["pubchem_sources"]["annotation_fields"]
    assert any(r["entity"] == "CHEBI:16236" and r["inchikey"] == key and
               r["validation"] == "STRICT_STRUCTURE_AGREES" for r in supplemental)
    broad = packet["records"]["chebi_class"]["data"]
    assert broad["default_structure"]["is_r_group"] and not broad["default_structure"]["standard_inchi"]


if __name__ == "__main__":
    packet = read(DATA / "authority_approved.json")
    native, supplemental, rejected, diagnostics = live_records(packet)
    verify_controls(packet, native, supplemental, diagnostics)
    data = {"http_requests": sum(r["attempts"] for r in packet["records"].values()),
            "usable_native_UNIIs": sorted(native), "supplemental": supplemental,
            "native_rejections": [{"UNII": r["UNII"], "reason": r["reason"]} for r in rejected],
            "diagnostics": diagnostics, "required_provider_controls": "PASS"}
    write(DATA / "v2" / "authority_validation.json", data)
    print(len(native), len(supplemental), len(rejected))
