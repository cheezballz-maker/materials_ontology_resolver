"""Collect independent NIST species facts for a frozen stratified review set."""

import argparse
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
from hashlib import sha256
import json
from html.parser import HTMLParser
import re
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from canonical_registry.authoritative_lookup.sources import file_digest, read, write
from canonical_registry.identity_sufficiency.contract import digest
from ..v3_authority import ROOT
from ..fixture import open_fixture, reader


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value.strip())


def freeze():
    fresh = read(ROOT / "fresh.json")
    queued = set(read(ROOT / "provider_queue.json").values())
    rows = []
    for group, limit in (("targeted_authority", 70), ("other", 22), ("scope_or_conflict", 18)):
        pool = [r for r in fresh if ((group == "targeted_authority" and r["concept_id"] in queued) or
                (group == "scope_or_conflict" and r["stratum"] in {"broad", "conflict"}) or
                (group == "other" and r["concept_id"] not in queued and r["stratum"] not in {"broad", "conflict"}))]
        for r in sorted(pool, key=lambda v: digest(["stage-c-v3-external-review", v["concept_id"]]))[:limit]:
            p = r["parent"]
            codes = [v for v in p["cas_nos"] or [] if isinstance(v, str) and v.strip()]
            rows.append({"referent": r["concept_id"], "designation": p["inci"], "description": p["description"],
                         "cas": codes[0] if len(codes) == 1 and re.fullmatch(r"\d{2,7}-\d{2}-\d", codes[0]) else None,
                         "stratum": group})
    write(ROOT / "reference_cohort.json", rows)


def acquire(root=ROOT, queue="reference_cohort.json", output="nist_reference.json"):
    path = root / output
    results = read(path) if path.exists() else {}
    for row in read(root / queue):
        cas = row["cas"]
        if cas is None or cas in results:
            continue
        url = "https://webbook.nist.gov/cgi/cbook.cgi?ID=C" + cas.replace("-", "")
        result = {"url": url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                  "status": "REFERENCE_FIELDS_UNAVAILABLE"}
        try:
            with urlopen(Request(url, headers={"User-Agent": "MaterialsOntology-StageC/3"}), timeout=8) as response:
                raw = response.read(800_001)
            result["sha256"] = sha256(raw).hexdigest()
            page = VisibleText()
            page.feed(raw.decode("utf-8", errors="replace"))
            text = " ".join(page.parts)
            key = re.search(r"IUPAC Standard InChIKey:\s*([A-Z-]{27})", text)
            inchi = re.search(r"IUPAC Standard InChI:\s*(InChI=1S/[^\s]+)", text)
            found_cas = re.search(r"CAS Registry Number:\s*([0-9-]+)", text)
            title = re.search(r"<title>(.*?)</title>", raw.decode("utf-8", errors="replace"), re.S)
            if key and found_cas and title and found_cas[1] == cas:
                result.update(status="STRUCTURAL_REFERENCE", inchikey=key[1], title=title[1].strip(),
                              cas=found_cas[1], inchi=inchi[1] if inchi else None)
        except (HTTPError, URLError, TimeoutError) as exc:
            result.update(status="RETRIEVAL_FAILED", failure=type(exc).__name__)
        results[cas] = result
        write(path, results)
        sleep(.35)
    print(len(results), "distinct CAS reference lookups")


def score(run):
    permit, _, _ = open_fixture(run)
    expected = read(ROOT / "reference_cohort.json")
    refs = read(ROOT / "nist_reference.json")
    with closing(reader(permit.path)) as db:
        decisions = {r["referent"]: r for value, in db.execute("SELECT result_json FROM stage_c_request")
                     for r in [json.loads(value)]}
    result = []
    for item in expected:
        row = decisions[item["referent"]]
        ref = refs.get(item["cas"], {})
        observed = row["eligibility"].get("specificity") or {}
        match = row["status"] == "RESOLVED_SUBSTANCE"
        # A reference tied only to a reported CAS verifies a chemical graph
        # when consistent. It cannot independently assign the source referent.
        reference = ref.get("inchikey")
        structural = ("AGREES" if observed.get("inchikey") == reference else "DIFFERS") if match and reference else (
            "REFERENCE_WITHOUT_EXACT_PREDICTION" if reference else "REFERENCE_UNAVAILABLE")
        result.append({**item, "reference": ref, "target": row.get("target"), "status": row["status"],
                       "structural_comparison": structural, "whole_referent_adjudicated": False})
    counts = Counter(r["structural_comparison"] for r in result)
    write(run / "reference_results.json", {"case_count": len(result), "counts": dict(counts),
           "cohort_sha256": file_digest(ROOT / "reference_cohort.json"),
           "reference_capture_sha256": file_digest(ROOT / "nist_reference.json"),
           "whole_referent_precision": None, "whole_referent_recall": None, "specialist_reviewed": 0, "cases": result})
    print(counts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("freeze", "acquire", "score"))
    parser.add_argument("--run", default="pilot-v3-verified")
    args = parser.parse_args()
    if args.action == "score":
        if not args.run.isascii() or not args.run.replace("-", "").isalnum():
            parser.error("Use a simple run name")
        score(ROOT.parent / args.run)
    else:
        (freeze if args.action == "freeze" else acquire)()
