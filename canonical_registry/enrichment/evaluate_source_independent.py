"""Real chemistry and actual transaction demonstration, confined to disposable copies."""
from contextlib import closing
from pathlib import Path
import json
import sqlite3
from time import perf_counter
from concurrent.futures import ThreadPoolExecutor

from .development import open_development, DEFAULT_DB, file_digest
from .workflow import Enrichment, ChemicalInput
from creation_transaction import CreationService

ROOT=Path(__file__).resolve().parents[1]
CASES=[
 ("water-structure",ChemicalInput("",smiles="O")),
 ("water-name",ChemicalInput("water")),
 ("water-alias",ChemicalInput("oxidane")),
 ("existing",ChemicalInput("bromomethane")),
 ("exact-stereo",ChemicalInput("",smiles="CC[C@H](C)O")),
 ("open-name",ChemicalInput("butan-2-ol")),
 ("open-graph",ChemicalInput("",smiles="CCC(C)O")),
 ("open-equivalent",ChemicalInput("",smiles="OC(CC)C")),
 ("partial-stereo",ChemicalInput("",smiles="C[C@H](O)C(O)CC")),
 ("unmodeled-tautomer",ChemicalInput("2-hydroxypropanoic acid")),
 ("broad-family",ChemicalInput("carboxylic acids")),
 ("ambiguous",ChemicalInput("essential oil mixture")),
 ("invalid",ChemicalInput("",smiles="O nonsense")),
 ("conflicting-graphs",ChemicalInput("water",smiles="CCO")),
 ("conflicting-key",ChemicalInput("",smiles="O",inchikey="LFQSCWFLJHTTHZ-UHFFFAOYSA-N")),
 ("identifier-only",ChemicalInput("",cas="7732-18-5")),
 ("unspecified-protonation",ChemicalInput("protonated or neutral glycine")),
 ("source-referent",ChemicalInput("water",source_system="ExampleSource",source_record_id="W1")),
]
def main():
 directory=ROOT/"enrichment/local/source_independent_evaluation_final"
 p,c=open_development(directory,create=True)
 protected=[DEFAULT_DB,ROOT/"output/registry.sqlite"]
 before={str(path):file_digest(path) for path in protected}
 rows=[]
 with Enrichment(directory) as service:
  data_hash=[file_digest(p.path),file_digest(c.path)]
  previews=service.batch([item for _,item in CASES])
  assert data_hash==[file_digest(p.path),file_digest(c.path)]
  for (name,item),preview in zip(CASES,previews,strict=True):
   receipt=service.commit(item,preview) if preview["commit_eligible"] else None
   rows.append({"case":name,"preview":preview,"commit":receipt})
   print(name,preview["outcome"],receipt["outcome"] if receipt else "-",flush=True)
  assert rows[0]["commit"]["outcome"]=="NEW_SUBSTANCE_CREATED"
  assert rows[1]["commit"]["committed_id"]==rows[0]["commit"]["committed_id"]==rows[2]["commit"]["committed_id"]
  assert rows[3]["commit"]["outcome"]=="EXISTING_SUBSTANCE_REUSED"
  assert all(not row["commit"] for row in rows[9:17])
  assert rows[5]["commit"]["committed_id"]==rows[6]["commit"]["committed_id"]==rows[7]["commit"]["committed_id"]
  retries=[service.commit(CASES[i][1],previews[i]) for i in (0,1,5)]
  _,qualified=service.input_adapter.interpret(ChemicalInput("",smiles="ClCCl"),service.local,service.bridge)
  db=sqlite3.connect(p.path.as_uri()+"?mode=ro",uri=True)
  inventory=db.execute("SELECT count(*) FROM substance_identity").fetchone()[0];db.close()
  def fail(stage):
   if stage=="AFTER_IDENTITY_INSERTION":raise RuntimeError("INJECTED_ROLLBACK")
  try:
   CreationService(p,service.bridge.official).execute(qualified,"rollback-test",failure_injector=fail)
   raise AssertionError("Transaction failure was not injected")
  except RuntimeError: pass
  with closing(sqlite3.connect(p.path.as_uri()+"?mode=ro",uri=True)) as db:
   assert db.execute("SELECT count(*) FROM substance_identity").fetchone()[0]==inventory
  with ThreadPoolExecutor(2) as pool:
   races=list(pool.map(lambda _:CreationService(p,service.bridge.official).execute(qualified,"race-test"),range(2)))
  assert sorted(r["outcome"] for r in races)==["EXISTING_SUBSTANCE_REUSED","NEW_SUBSTANCE_CREATED"]
  for kind in ("pubchem","chebi"):
   packet=json.loads((ROOT/f"canonical_substance_creation/examples/{kind}_creation_input.json").read_text(encoding="utf-8-sig"))
   item=ChemicalInput("propan-2-yl 2-hydroxybenzoate")
   preview=service.resolve(item,saved_evidence=packet);receipt=service.commit(item,preview,saved_evidence=packet)
   rows.append({"case":kind,"preview":preview,"commit":receipt})
   print(kind,preview["outcome"],receipt["outcome"],flush=True)
   assert receipt["committed_id"]
  with Enrichment(directory,max_candidates=1) as limited:
   incomplete=limited.resolve(ChemicalInput("",smiles="CCN"))
   assert incomplete["outcome"]=="INCOMPLETE_SEARCH" and not incomplete["commit_eligible"]
 after={str(path):file_digest(path) for path in protected}
 assert before==after
 integrity={}
 for name,path in (("substances",p.path),("concepts",c.path)):
  with closing(sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)) as db:
   integrity[name]={"integrity":db.execute("PRAGMA integrity_check").fetchall(),"foreign_keys":db.execute("PRAGMA foreign_key_check").fetchall()}
 output={"registry_paths":{"substance":str(p.path),"concept":str(c.path)},"records":rows,"retries":retries,"concurrency":[{k:r[k] for k in ("outcome","substance_id")} for r in races],"rollback_verified":True,"incomplete":incomplete,"preview_unchanged":True,"protected_before":before,"protected_after":after,"integrity":integrity}
 (ROOT/"enrichment/source_independent_evaluation.json").write_text(json.dumps(output,indent=2)+"\n")
if __name__=="__main__": main()
