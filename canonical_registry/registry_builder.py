"""Five-table snapshot writer; complete-link comparison and stable-ID reuse."""
from pathlib import Path
from contextlib import closing
import sqlite3
from chemistry import describe
from identity_comparator import compare
from resolver import lookup

def populate(reg,accepted,reconciliations,base_registry=None):
    existing=[];next_number=1
    if base_registry and Path(base_registry).exists():
        with closing(sqlite3.connect(Path(base_registry).resolve().as_uri()+'?mode=ro',uri=True)) as old:
            existing=[(sid,describe(s)) for sid,s in old.execute("SELECT substance_id,structure_value FROM substance_structure WHERE structure_type='SMILES'")]
            ids=[int(s[4:]) for (s,) in old.execute('SELECT substance_id FROM substance_identity') if s.startswith('SUB_') and s[4:].isdigit()]
            next_number=max(ids,default=0)+1
    clusters=[]
    for record in sorted(accepted,key=lambda r:r['i']):
        # Complete-link, not a transitive union of ambiguous edges or hash matches.
        matches=[g for g in clusters if all(compare(record['d'],r['d'])['assessment']=='EXACT' for r in g)]
        if len(matches)==1:matches[0].append(record)
        elif not matches:clusters.append([record])
        else:raise ValueError('Non-equivalence in clustering; refusing transitive merge')
    mapping={};blocked={};count=0;new_count=0
    for group in clusters:
        d=group[0]['d'];found=lookup(d,existing)
        if found['status']=='UNRESOLVED':
            blocked.update({r['i']:'AMBIGUOUS_EXISTING_CANONICAL_IDENTITY' for r in group});continue
        if found['status']=='EXACT':sid=found['substance_id']
        else:sid=f'SUB_{next_number:08d}';next_number+=1;new_count+=1
        # A stable ID can be reached through multiple representation buckets only
        # after all-to-all validation, never by shared identifiers or names.
        if reg.execute('SELECT 1 FROM substance_identity WHERE substance_id=?',(sid,)).fetchone():raise ValueError('Duplicate exact cluster for an existing identity')
        name=min(group,key=lambda r:(len(r['name']),r['name'].casefold(),r['i']))['name']
        reg.execute('INSERT INTO substance_identity VALUES(?,?,?)',(sid,name,'ACCEPTED'));count+=1
        for r in group:
            mapping[r['i']]=sid;g=r['d']
            for alias in [r['name']]+r['aliases']:reg.execute('INSERT OR IGNORE INTO substance_alias VALUES(?,?)',(sid,alias))
            reg.execute('INSERT OR IGNORE INTO substance_structure VALUES(?,?,?)',(sid,'SMILES',g['smiles']))
            for typ,val in [('InChI',g['inchi']),('InChIKey',g['inchikey']),('FixedHInChI',g['fixed_h_inchi'])]:
                reg.execute('INSERT OR IGNORE INTO substance_identifier VALUES(?,?,?)',(sid,typ,val))
            for row in r['external'].get('rows',[]):
                for field,typ in [('CID','PubChemCID'),('ChEBIID','ChEBIID'),('UNII','UNII'),('DTXSID','DTXSID'),('DTXCID','DTXCID')]:
                    if row.get(field):reg.execute('INSERT OR IGNORE INTO substance_identifier VALUES(?,?,?)',(sid,typ,str(row[field])))
    for i,status,reason in reconciliations:
        if i in blocked:status,reason='UNRESOLVED',blocked[i]
        reg.execute('INSERT INTO substance_reconciliation VALUES(?,?,?,?)',(i,mapping.get(i),status,reason))
    return dict(canonical_substances=count,new_substances=new_count,reused_substances=count-new_count,
                multi_cuma_exact_clusters=sum(len(g)>1 and g[0]['i'] in mapping for g in clusters),blocked=blocked,mapping=mapping)
