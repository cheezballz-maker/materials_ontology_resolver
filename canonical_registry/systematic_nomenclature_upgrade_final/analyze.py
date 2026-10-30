"""Summarize source-state changes and coarse report-only triage."""
import collections,json,re,sqlite3
from pathlib import Path
H=Path(__file__).resolve().parent;B=H.parent
read=lambda p:json.loads(Path(p).read_text(encoding="utf-8"))
old={x["cuma_index"]:x for x in read(B/"name_interpretation_architecture/comparison.json")};new=read(H/"comparison.json")
trans=collections.Counter();triage=[];mappings=collections.Counter();detail=[]
c=sqlite3.connect((H/"run/candidates.sqlite").as_uri()+"?mode=ro",uri=True)
for i,raw in c.execute("select cuma_index,evidence_json from candidate"):
 ev=json.loads(raw);profile=ev.get("source_name_profile",{});mapping=profile.get("stereo_locant_mapping")
 if mapping:mappings[mapping["status"]]+=1
 ccase=next(x for x in new if x["cuma_index"]==i);before=old[i].get("name_interpretation",{}).get("status","MISSING");after=ccase.get("name_interpretation",{}).get("status","MISSING");trans[(before,after)]+=1
 if before!=after:detail.append(dict(cuma_index=i,name=ccase["preferred_name"],before=before,after=after,mapping=mapping,resolution_before=old[i]["predicted_status"],resolution_after=ccase["predicted_status"]))
 if after!="UNKNOWN":continue
 name=ccase["preferred_name"];reason=ccase["resolver_reason"]
 if "INCOMPLETE_SOURCE_REFERENT" in reason or "MALFORMED" in reason:cat="MALFORMED_OR_INCOMPLETE_NAME"
 elif ccase["predicted_status"] in ("OUT_OF_SCOPE","INVALID"):cat="OTHER_EXISTING_CAPABILITY_GAP"
 elif re.search(r"\d|[\[\]{}]|,",name):cat="SYSTEMATIC_NOTATION_STILL_UNSUPPORTED"
 elif re.fullmatch(r"[A-Za-z]+(?:[ -][A-Za-z]+)?",name):cat="COMMON_NAME_EVIDENCE_REQUIRED"
 else:cat="OTHER_EXISTING_CAPABILITY_GAP"
 triage.append(dict(cuma_index=i,name=name,category=cat,resolver_status=ccase["predicted_status"],diagnostic=ccase["name_interpretation"].get("diagnostic")))
result=dict(transitions={a+" -> "+b:n for (a,b),n in sorted(trans.items())},unknown_remaining=sum(x["name_interpretation"].get("status")=="UNKNOWN" for x in new),mapping_counts=dict(mappings),triage_counts=dict(collections.Counter(x["category"] for x in triage)),changes=detail,triage=triage)
(H/"interpretation_analysis.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({k:v for k,v in result.items() if k not in ("triage",)},ensure_ascii=False,indent=2))
