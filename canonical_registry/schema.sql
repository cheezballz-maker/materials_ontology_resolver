PRAGMA foreign_keys=ON;
CREATE TABLE substance_identity(substance_id TEXT PRIMARY KEY, preferred_name TEXT NOT NULL, identity_status TEXT NOT NULL CHECK(identity_status='ACCEPTED'));
CREATE TABLE substance_alias(substance_id TEXT NOT NULL REFERENCES substance_identity, alias TEXT NOT NULL, PRIMARY KEY(substance_id,alias));
CREATE TABLE substance_identifier(substance_id TEXT NOT NULL REFERENCES substance_identity, identifier_type TEXT NOT NULL, identifier_value TEXT NOT NULL, PRIMARY KEY(substance_id,identifier_type,identifier_value));
CREATE TABLE substance_structure(substance_id TEXT NOT NULL REFERENCES substance_identity, structure_type TEXT NOT NULL, structure_value TEXT NOT NULL, PRIMARY KEY(substance_id,structure_type,structure_value));
CREATE TABLE substance_reconciliation(cuma_index INTEGER PRIMARY KEY, substance_id TEXT REFERENCES substance_identity, resolution_status TEXT NOT NULL CHECK(resolution_status IN ('EXACT','UNRESOLVED','CONFLICT','OUT_OF_SCOPE','INVALID')), reason TEXT NOT NULL, CHECK((resolution_status='EXACT')=(substance_id IS NOT NULL)));
