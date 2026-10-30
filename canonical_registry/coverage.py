"""Generate aggregate-only Trino SQL from the accepted registry; never retrieve legacy rows."""
import sqlite3
from pathlib import Path
from providers import ROOT

def lit(v): return "'"+v.replace("'","''")+"'"
def values(rows): return ',\n'.join('('+','.join(lit(str(v)) for v in row)+')' for row in rows)

def generate(output=ROOT/'output'):
    output=Path(output); db=sqlite3.connect(output/'registry.sqlite')
    ids=db.execute('SELECT substance_id FROM substance_identity ORDER BY substance_id').fetchall()
    keys=db.execute("SELECT substance_id,identifier_value FROM substance_identifier WHERE identifier_type='InChIKey'").fetchall()
    aliases=db.execute('SELECT substance_id,alias FROM substance_alias').fetchall()
    cas=db.execute("SELECT substance_id,identifier_value FROM substance_identifier WHERE identifier_type='CASRegistryNumber'").fetchall()
    if not ids: raise ValueError('No accepted registry; coverage denominator is zero')
    keyfilter=','.join(lit(k) for _,k in keys)
    aliasvalues=sorted({a for _,a in aliases})
    # Trino/JVM limits arguments in one array constructor. Keep each below 100.
    aliasarray=' || '.join('ARRAY['+','.join(lit(a) for a in aliasvalues[n:n+100])+']' for n in range(0,len(aliasvalues),100))
    sql=f"""-- Read only; exact literal alias presence is NOT canonical equivalence.
-- No source substance_id is returned or reconciled. No row download.
WITH canonical(substance_id) AS (VALUES {values(ids)}),
registry_keys(substance_id, value) AS (VALUES {values(keys)}),
registry_aliases(substance_id, value) AS (VALUES {values(aliases)}),
key_hits AS (
 SELECT DISTINCT r.substance_id, 'InChIKey' AS channel
 FROM registry_keys r JOIN pd_dw.dws_material_substance_entity_v2 l ON l.inchi_key=r.value
 WHERE l.inchi_key IN ({keyfilter})
),
legacy_alias_values AS (
 SELECT DISTINCT matched_alias
 FROM pd_dw.dws_material_substance_entity_v2 l
 CROSS JOIN UNNEST(array_intersect(
   coalesce(l.substance_name_all, CAST(ARRAY[] AS ARRAY(VARCHAR))) ||
   ARRAY[l.substance_master_name_en, l.iupac_name, l.jchem_name, l.compound_name, l.scientificname],
   {aliasarray})) AS a(matched_alias)
),
alias_hits AS (
 SELECT DISTINCT r.substance_id, 'alias' AS channel
 FROM registry_aliases r JOIN legacy_alias_values l ON r.value=l.matched_alias
),
"""
    if cas:
        casfilter=','.join(lit(v) for _,v in cas)
        sql+=f"""registry_cas(substance_id,value) AS (VALUES {values(cas)}),
cas_hits AS (
 SELECT DISTINCT r.substance_id, 'CAS' AS channel FROM registry_cas r
 JOIN (SELECT DISTINCT v FROM pd_dw.dws_material_substance_entity_v2 l
 CROSS JOIN UNNEST(array_intersect(coalesce(l.cas_rn,CAST(ARRAY[] AS ARRAY(VARCHAR))),ARRAY[{casfilter}])) AS t(v)) l ON r.value=l.v
),
hits AS (SELECT * FROM key_hits UNION ALL SELECT * FROM alias_hits UNION ALL SELECT * FROM cas_hits),
"""
    else: sql+="hits AS (SELECT * FROM key_hits UNION ALL SELECT * FROM alias_hits),\n"
    sql+="""per_substance AS (
 SELECT c.substance_id, count(DISTINCT h.channel) AS channels,
 max(CASE WHEN h.channel='InChIKey' THEN 1 ELSE 0 END) AS key_match,
 max(CASE WHEN h.channel='CAS' THEN 1 ELSE 0 END) AS cas_match,
 max(CASE WHEN h.channel='alias' THEN 1 ELSE 0 END) AS alias_match
 FROM canonical c LEFT JOIN hits h ON c.substance_id=h.substance_id GROUP BY c.substance_id
)
SELECT count(*) AS canonical_substances,
 count_if(channels>0) AS matched_any_channel,
 count_if(channels=0) AS not_matched,
 CAST(count_if(channels>0) AS DOUBLE)/count(*) AS coverage,
 sum(key_match) AS inchikey_match,
 sum(cas_match) AS cas_identifier_match,
 sum(alias_match) AS alias_match,
 count_if(channels>1) AS multiple_channel_match
FROM per_substance
LIMIT 1
"""
    (output/'legacy_coverage.sql').write_text(sql,encoding='utf-8'); print('Generated aggregate-only coverage SQL for',len(ids),'canonical identities; CAS-eligible:',len(cas))

if __name__=='__main__': generate()
