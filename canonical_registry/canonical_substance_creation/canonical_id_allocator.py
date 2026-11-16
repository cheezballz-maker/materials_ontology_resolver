"""Opaque monotone IDs allocated only inside the reserved write transaction."""
def allocate(db):
 if not db.in_transaction:raise ValueError('ID_ALLOCATION_REQUIRES_TRANSACTION')
 n=db.execute('SELECT high_water FROM canonical_id_sequence WHERE singleton=1').fetchone()[0]+1
 while db.execute('SELECT 1 FROM substance_identity WHERE substance_id=?',(f'SUB_{n:08d}',)).fetchone():n+=1
 if n>99999999:raise OverflowError('SUB_NAMESPACE_EXHAUSTED')
 db.execute('UPDATE canonical_id_sequence SET high_water=? WHERE singleton=1',(n,))
 return f'SUB_{n:08d}'
