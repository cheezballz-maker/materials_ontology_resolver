"""Report-only classification of detectable stereo-related unresolved cases."""
import json,sqlite3,collections
from pathlib import Path
H=Path(__file__).resolve().parent;c=sqlite3.connect((H/"run/candidates.sqlite").as_uri()+"?mode=ro",uri=True)
items=[]
for i,name,status,reason,raw in c.execute("select cuma_index,name,status,diagnostic,evidence_json from candidate order by cuma_index"):
 if status=="EXACT":continue
 e=json.loads(raw);p=e.get("source_name_profile",{});feat=p.get("source_features",{});n=p.get("nomenclature",{});m=p.get("stereo_locant_mapping") or {};state=e.get("name_interpretation",{}).get("status")
 stereo=bool(n.get("descriptors") or n.get("relative_stereo") or n.get("configurational_series") or feat.get("absolute_stereo_descriptors") or feat.get("dl_descriptor"))
 if not stereo:continue
 if m.get("reason") in ("LOCANT_SCOPE_UNRESOLVED","LOCANT_NOT_UNIQUE","GRAPH_MAPPING_AMBIGUOUS"):category="LOCANT_SCOPE_UNRESOLVED"
 elif state=="PARTIAL":category="SOURCE_STEREO_PARTIAL"
 elif state=="UNKNOWN":category="SOURCE_NOTATION_UNSUPPORTED"
 else:category="OTHER_DOWNSTREAM_GAP"
 items.append(dict(cuma_index=i,name=name,status=status,reason=reason,name_interpretation=state,mapping_status=m.get("status"),mapping_reason=m.get("reason"),category=category))
out=dict(method="Report-only triage for explicit lexical stereo markers; not exhaustive for common names",counts=dict(collections.Counter(x["category"] for x in items)),cases=items)
(H/"stereo_triage.json").write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(out["counts"],indent=2))
