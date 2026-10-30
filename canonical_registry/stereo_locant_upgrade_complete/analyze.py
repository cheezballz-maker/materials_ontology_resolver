"""Read-only development comparison of source mapping and consumption."""
import json,sqlite3,collections,sys
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent;sys.path.insert(0,str(B))
from form_characterizer import interpret
read=lambda p:json.loads(p.read_text(encoding="utf-8"))
old=sqlite3.connect((B/"systematic_nomenclature_upgrade_final/run/candidates.sqlite").as_uri()+"?mode=ro",uri=True)
new=sqlite3.connect((H/"run/candidates.sqlite").as_uri()+"?mode=ro",uri=True)
before={i:(s,json.loads(raw)) for i,s,raw in old.execute("select cuma_index,status,evidence_json from candidate")}
trans=collections.Counter();prior=collections.Counter();after=collections.Counter();details=[];records=[];consumed=0;gate_consumed=0;scoped=0
for i,name,status,raw in new.execute("select cuma_index,name,status,evidence_json from candidate order by cuma_index"):
 ev=json.loads(raw);old_status,old_ev=before[i];bp=old_ev.get("source_name_profile",{});ap=ev.get("source_name_profile",{});bm=bp.get("stereo_locant_mapping") or {};am=ap.get("stereo_locant_mapping") or {}
 bs=old_ev.get("name_interpretation",{}).get("status","MISSING");ns=ev.get("name_interpretation",{}).get("status","MISSING");trans[(bs,ns)]+=1
 if bm:prior[bm.get("reason",bm.get("status"))]+=1
 if am:after[am.get("reason",am.get("status"))]+=1
 if am.get("status")=="MAPPED":
  source=ev["claims"][0].get("structure");assert source
  used=interpret(source,name,source_profile=ap)["source_stereo_used"]
  recorded=ev.get("decision",{}).get("form",{}).get("source_stereo_used",False)
  assert recorded==used,(i,recorded,used)
  consumed+=bool(recorded)
  gate_used=ev.get("source_form",{}).get("source_stereo_used",False);gate_consumed+=bool(gate_used)
  scoped+=any(x.get("scope")=="UNIQUE_SOURCE_STEREOGENIC_LOCANT" for x in am.get("mappings",[]))
  records.append(dict(cuma_index=i,name=name,status=status,reason=ev.get("decision",{}).get("reason_codes"),mapping=am,downstream_form_recorded=bool(recorded),downstream_form_rechecked=bool(used),gate_used=gate_used))
 if bs!=ns or old_status!=status or bm.get("reason")!=am.get("reason"):
  details.append(dict(cuma_index=i,name=name,before_status=old_status,after_status=status,before_interpretation=bs,after_interpretation=ns,before_mapping=bm,after_mapping=am,reason=ev.get("decision",{}).get("reason_codes")))
summary=dict(transitions={a+" -> "+b:n for (a,b),n in sorted(trans.items())},prior_mapping=dict(prior),after_mapping=dict(after),mapped_records=len(records),form_consumed_rechecked=consumed,gate_consumed_recorded=gate_consumed,topology_scoped_records=scoped,details=details,mapped_records_detail=records)
(H/"stereo_analysis.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in summary.items() if k not in ("details","mapped_records_detail")},indent=2));print("CHANGES",[(x["cuma_index"],x["before_status"],x["after_status"],x["before_interpretation"],x["after_interpretation"]) for x in details])
