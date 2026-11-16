"""Bounded public authority probes and versioned JSON captures."""

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import socket
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, getproxies, urlopen

DATA = Path(__file__).resolve().parents[1] / "data"
GSRS = "https://gsrs.ncats.nih.gov/ginas/app/api/v1/"
PUBCHEM = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/"
CHEBI = "https://www.ebi.ac.uk/chebi/backend/api/public/"
PROPERTIES = "/property/SMILES,InChI,InChIKey,IUPACName/JSON"
PROBES = {
    "gsrs_ethanol": GSRS + "substances(10dfa22e-ca56-40bf-b0b5-4f92a36ede90)?view=full",
    "gsrs_glycerol": GSRS + "substances/search?" + urlencode({"q": "root_approvalID:PDC6A3C0OX", "top": 3}),
    "pubchem_name": PUBCHEM + "name/ethanol" + PROPERTIES,
    "pubchem_cid": PUBCHEM + "cid/702" + PROPERTIES,
    "pubchem_structure": PUBCHEM + "fastidentity/smiles/CCO/cids/JSON?identity_type=same_stereo_isotope&MaxRecords=9",
    "pubchem_synonyms": PUBCHEM + "cid/702/synonyms/JSON",
    "pubchem_sources": PUBCHEM + "cid/702/sids/JSON",
    "pubchem_multiple": PUBCHEM + "name/glutamic%20acid/cids/JSON?name_type=word&MaxRecords=12",
    "chebi_ethanol": CHEBI + "compound/CHEBI:16236/",
    "chebi_class": CHEBI + "compound/CHEBI:30879/",
}


def write(path, data):
    temporary = path.with_suffix(".pending")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def capture(url):
    host = urlsplit(url).hostname
    result = {"hostname": host, "url": url, "method": "GET",
              "retrieved_at": datetime.now(timezone.utc).isoformat()}
    started = time.monotonic()
    try:
        socket.getaddrinfo(host, 443)
        result["dns"] = "RESOLVED"
    except socket.gaierror as exc:
        result.update(dns="FAILED", dns_error=type(exc).__name__, dns_code=exc.errno)
    for attempt in range(2):
        try:
            request = Request(url, headers={"Accept": "application/json", "User-Agent": "MaterialsOntology-StageC/2"})
            with urlopen(request, timeout=15, context=ssl.create_default_context()) as response:
                raw = response.read(4_000_001)
                result.update(http_status=response.status, response_type=response.headers.get("Content-Type"),
                              response_date=response.headers.get("Date"), transport="HTTPS_VERIFIED")
            if len(raw) > 4_000_000:
                raise ValueError("RESPONSE_SIZE_LIMIT")
            data = json.loads(raw)
            result.update(status="JSON_CAPTURED", sha256=sha256(raw).hexdigest(), data=data)
            break
        except HTTPError as exc:
            result.update(status="RATE_LIMITED" if exc.code == 429 else "HTTP_ERROR", http_status=exc.code,
                          exception=type(exc).__name__)
            if exc.code not in (429, 503) or attempt:
                break
            delay = exc.headers.get("Retry-After", "")
            if delay and (not delay.isdecimal() or int(delay) > 10):
                break
            time.sleep(int(delay) if delay else 1)
        except URLError as exc:
            reason = exc.reason
            status = ("DNS_FAILURE" if isinstance(reason, socket.gaierror) else
                      "TLS_FAILURE" if isinstance(reason, ssl.SSLError) else
                      "TIMEOUT" if isinstance(reason, TimeoutError) else "TRANSPORT_FAILURE")
            result.update(status=status, exception=type(reason).__name__, code=getattr(reason, "errno", None))
            break
        except (ValueError, TimeoutError) as exc:
            result.update(status="TIMEOUT" if isinstance(exc, TimeoutError) else "RESPONSE_INVALID",
                          exception=type(exc).__name__)
            break
    return {**result, "attempts": attempt + 1, "seconds": time.monotonic() - started}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", choices=("sandbox", "approved"), required=True)
    parser.add_argument("--queue", type=Path)
    parser.add_argument("--capture-file", type=Path)
    args = parser.parse_args()
    path = args.capture_file or DATA / ("authority_" + args.run + ".json")
    probes = dict(PROBES)
    if args.queue:
        queue = json.loads(args.queue.read_text(encoding="utf-8"))
        if (not isinstance(queue, list) or len(queue) > 80 or
            any(not isinstance(s, str) or len(s) != 10 or not s.isascii() or not s.isalnum() for s in queue)):
            raise ValueError("EXPECTED_BOUNDED_PUBLIC_UNII_QUEUE")
        probes.update({"unii_" + s: GSRS + "substances/search?" +
                       urlencode({"q": "root_approvalID:" + s, "top": 3}) for s in queue})
    packet = {"environment": {"network_disabled_marker": os.getenv("CODEX_SANDBOX_NETWORK_DISABLED"),
                              "platform": platform.system(), "python": platform.python_version(),
                              "tls": ssl.OPENSSL_VERSION, "proxy_schemes": sorted(getproxies())}, "records": {}}
    if path.exists():
        packet = json.loads(path.read_text(encoding="utf-8"))
    for name, url in list(probes.items()):
        if name not in packet["records"]:
            packet["records"][name] = capture(url)
            time.sleep(.25)
            write(path, packet)
        record = packet["records"][name]
        if name == "gsrs_glycerol" or name.startswith("unii_"):
            data = record.get("data", {})
            hits = data.get("content", [])
            if data.get("total") == 1 and len(hits) == 1:
                uuid = hits[0].get("uuid", "")
                detail = name + "_native"
                if len(uuid) == 36 and all(c in "0123456789abcdef-" for c in uuid) and detail not in packet["records"]:
                    packet["records"][detail] = capture(GSRS + "substances(" + quote(uuid) + ")?view=full")
                    write(path, packet)
                    time.sleep(.25)
        print(name, record["status"], record.get("http_status"), flush=True)


if __name__ == "__main__":
    main()
