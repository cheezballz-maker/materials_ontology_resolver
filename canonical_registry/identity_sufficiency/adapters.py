"""Translate observed source roles into the shared evidence contract."""

from canonical_registry.chemistry import describe
from canonical_registry.cosing_pilot.stage_b_handoff import broad_scope, Trace
from .contract import Claim, Evidence, WHOLE, digest, structure_signature

UNKNOWN = "SCOPE_UNESTABLISHED"
COSING_DOC = "https://single-market-economy.ec.europa.eu/sectors/cosmetics/cosmetic-ingredient-database_en"
GSRS_DOC = "https://gsrs.ncats.nih.gov/api-documentation"


def _claim(id,kind,value,entity,authority,document,locator,revision,scope=UNKNOWN,
           grants=(),namespace="",identity_scope="",binding_revision=""):
    return Claim(str(id),kind,value,scope,entity,authority or "",tuple(grants),document,
                 locator,revision,namespace,identity_scope,binding_revision)


def _curated_structure(receipt, revision):
    nist = receipt["structure"]
    entity = receipt["entity"]
    return [
        _claim("reference:graph","INCHI",nist["inchi"],entity,"NIST Chemistry WebBook",
               nist["url"],"Standard InChI",revision,grants=("STRUCTURE",)),
        _claim("reference:key","INCHIKEY",nist["key"],entity,"NIST Chemistry WebBook",
               nist["url"],"InChIKey",revision,grants=("STRUCTURE",)),
        _claim("reference:formula","FORMULA",nist["formula"],entity,"NIST Chemistry WebBook",
               nist["url"],"Formula",revision,grants=("STRUCTURE",)),
    ]


def _cosing_receipt(receipt, parent, row, trace):
    required = receipt["source_conditions"]
    if (receipt["source_revision"]!=row["revision"] or parent["inci"]!=required["designation"]
            or parent["description"]!=required["definition"] or parent["cas_nos"]!=required["cas"]
            or parent["ec_nos"]!=required["ec"]):
        return [],["CURATED_SOURCE_BINDING_REVISION_MISMATCH"]
    if trace.guard or trace.withheld or trace.p0:
        return [],["CURATED_SOURCE_BINDING_CONTRADICTS_STAGE_B_SCOPE"]
    graph = describe(receipt["structure"]["inchi"],"inchi")
    if any(structure_signature(c["value"])!=structure_signature(graph) for c in trace.graphs):
        return [],["CURATED_REFERENCE_GRAPH_DISAGREES_WITH_STAGE_B"]
    claims = _curated_structure(receipt,digest(receipt))
    bridge = receipt["binding"]
    claims.append(_claim("reference:binding",bridge["kind"],bridge["value"],receipt["entity"],
                         bridge["authority"],bridge["url"],bridge["locator"],row["revision"],WHOLE,
                         tuple(bridge["grants"]),bridge.get("namespace",""),"DEFINED_CHEMICAL"))
    return claims,[]


def cosing(row, parent, aliases, receipt=None):
    ref,rev,cid = row["source_reference"],row["revision"],row["concept_id"]
    trace = Trace(row["attributes"],row["summary"],row["trace"])
    claims = [_claim("designation","NAME",parent["inci"],cid,"CosIng",COSING_DOC,
                     ref+"#designation",rev,grants=("SOURCE_RECORD",))]
    if parent["description"]:
        claims.append(_claim("definition","DEFINITION",parent["description"],cid,"CosIng",
                             COSING_DOC,ref+"#definition",rev,grants=("SOURCE_RECORD",)))
    for namespace,key in (("CAS","cas_nos"),("EC","ec_nos")):
        claims.extend(_claim(f"{key}:{i}","IDENTIFIER",v,cid,"CosIng",COSING_DOC,
                             f"{ref}#{key}[{i}]",rev,namespace=namespace)
                      for i,v in enumerate(parent[key] or []) if isinstance(v,str) and v.strip())
    alias_types = {"SMILES":"SMILES","INCHI":"INCHI","INCHI_KEY":"INCHIKEY","MOLECULAR_FORMULA":"FORMULA",
                   "CAS_NO":"IDENTIFIER","EC_NO":"IDENTIFIER"}
    for alias in aliases:
        kind = alias_types.get(alias["alias_type"])
        if kind and isinstance(alias["alias"],str) and alias["alias"].strip():
            id = alias["inci_alias_id"]
            claims.append(_claim(id,kind,alias["alias"],cid,alias["source"],COSING_DOC,id,digest(alias)))
    for j,c in enumerate(trace.graphs+trace.withheld):
        if c["method"]=="OPSIN_THEN_STRICT_RDKIT":
            claims.append(_claim(f"stage-b:{j}","SMILES",c["value"]["smiles"],cid,"OPSIN",
                                row.get("stage_b_version") or "stage-b",c["evidence"]["source_reference"],rev))
    holds = []
    if not row.get("stage_b_version"):
        holds.append("STAGE_B_PROCESSING_INCOMPLETE")
    if trace.summary.get("state")=="CONFLICT" or "P1" in row["old_evidence"]["risk_priorities"]:
        holds.extend(sorted(trace.issues) or ["IDENTITY_SIGNIFICANT_REVIEW"])
    if receipt:
        extra,reasons = _cosing_receipt(receipt,parent,row,trace)
        claims.extend(extra)
        holds.extend(reasons)
    scope = broad_scope(parent,trace)
    return Evidence(cid,ref,rev,parent["inci"],tuple(claims),"BROAD" if scope else "UNESTABLISHED",
                    (scope,) if scope else (),tuple(sorted(set(holds))))


def gsrs(row, companions, receipt=None, native=None):
    cid = row["chemical_id"]
    ref = "mse_dwd.dwd_mse_chemicals_inventory:"+cid
    rev = digest(row)
    claims = [_claim("name","NAME",row["chemical_name"],cid,row["source"],GSRS_DOC,ref+"#chemical_name",rev,
                     grants=("SOURCE_RECORD",))]
    for field,kind in (("smiles","SMILES"),("molecular_formula","FORMULA"),("inchikey","INCHIKEY")):
        if row.get(field):
            claims.append(_claim(field,kind,row[field],cid,row["source"],GSRS_DOC,ref+"#"+field,rev,
                "CONSTITUENT" if row["ingredient_type"] in {"IONIC MOIETY","MOLECULAR FRAGMENT"} else UNKNOWN))
    for idrow in companions.get("identifiers",[]):
        if idrow[3]:
            claims.append(_claim(idrow[0],"IDENTIFIER",idrow[3],cid,idrow[5],GSRS_DOC,idrow[0],
                                 digest(idrow),namespace=idrow[2] or ""))
    for alias in companions.get("aliases",[]):
        if alias[3]:
            claims.append(_claim("alias:"+alias[0],"REPORTED_NAME",alias[3],cid,alias[6],GSRS_DOC,
                                 alias[0],digest(alias),namespace=alias[2] or ""))
    holds = []
    if receipt:
        if (receipt["unii"]!=row["source_id"] or receipt["preferred_name"]!=row["chemical_name"]
                or row["substance_type"]!="chemical" or row["ingredient_type"]!="INGREDIENT SUBSTANCE"):
            holds.append("FDA_RECORD_IDENTITY_OR_ROLE_MISMATCH")
        else:
            graph = describe(receipt["structure"]["inchi"],"inchi")
            try:
                compatible = (structure_signature(describe(row["smiles"]))==structure_signature(graph) and
                              row.get("inchikey")==receipt["fda_key"]==graph["inchikey"] and
                              receipt["fda_formula"]==graph["formula"])
            except (ValueError,RuntimeError):
                compatible = False
            if compatible:
                claims.extend(_curated_structure(receipt,digest(receipt)))
                claims.append(_claim("fda:unii","IDENTIFIER_LINK",row["source_id"],receipt["entity"],
                    "FDA UNII Search Service",receipt["fda_url"],"UNII and Preferred Substance Name",rev,WHOLE,
                    ("IDENTIFIER","REFERENT"),"UNII","DEFINED_CHEMICAL"))
            else:
                holds.append("FDA_OR_NIST_STRUCTURE_COMPARISON_DISAGREES")
    if native:
        if (row["source_id"]!=native["UNII"] or row["substance_type"]!="chemical" or
                row["ingredient_type"]!="INGREDIENT SUBSTANCE" or not native["structure_references"]):
            holds.append("NATIVE_RECORD_IDENTITY_OR_ROLE_MISMATCH")
        else:
            try:
                same = structure_signature(describe(row["smiles"]))==structure_signature(describe(native["SMILES"]))
            except (ValueError,RuntimeError):
                same = False
            if not same or row["inchikey"]!=native["InChIKey"]:
                holds.append("NATIVE_AND_WAREHOUSE_STRUCTURE_DISAGREE")
            else:
                claims.append(_claim("native:structure","SMILES",native["SMILES"],"UNII:"+native["UNII"],
                    "NCATS GSRS native structure",native["url"],"structure; integer moieties; references",digest(native),
                    WHOLE,("STRUCTURE","REFERENT","COMPLETE_COMPOSITION"),binding_revision=rev))
    material = {"mixture":"MIXTURE","polymer":"POLYMER","structurallyDiverse":"VARIABLE"}.get(row["substance_type"])
    return Evidence(cid,ref,rev,row["chemical_name"],tuple(claims),material or "UNESTABLISHED",
                    (ref+"#substance_type",) if material else (),tuple(holds))
