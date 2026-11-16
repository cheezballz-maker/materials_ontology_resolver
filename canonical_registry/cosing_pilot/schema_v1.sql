PRAGMA application_id=1129272143;
PRAGMA user_version=1;

CREATE TABLE domain_type(
    name TEXT PRIMARY KEY,
    id_prefix TEXT NOT NULL UNIQUE,
    last_id INTEGER NOT NULL DEFAULT 0 CHECK(last_id BETWEEN 0 AND 99999999)
);
CREATE TABLE domain_concept(
    concept_id TEXT PRIMARY KEY,
    domain_type TEXT NOT NULL REFERENCES domain_type(name),
    preferred_label TEXT NOT NULL CHECK(length(trim(preferred_label))>0),
    label_key TEXT NOT NULL,
    source_reference TEXT NOT NULL UNIQUE,
    registered_revision TEXT NOT NULL,
    canonical_status TEXT NOT NULL DEFAULT 'NOT_EVALUATED'
        CHECK(canonical_status IN ('NOT_EVALUATED','RESOLVED_SUBSTANCE','RESOLVED_CHEMICAL_CONCEPT','UNRESOLVED')),
    canonical_target_json TEXT CHECK(canonical_target_json IS NULL OR json_valid(canonical_target_json)),
    CHECK(COALESCE(
        CASE canonical_status
        WHEN 'NOT_EVALUATED' THEN canonical_target_json IS NULL
        WHEN 'UNRESOLVED' THEN canonical_target_json IS NULL
        ELSE json_type(canonical_target_json,'$.id')='text'
          AND substr(json_extract(canonical_target_json,'$.id'),-8) NOT GLOB '*[^0-9]*'
          AND json_type(canonical_target_json,'$.registry_key')='text'
          AND length(json_extract(canonical_target_json,'$.registry_key'))>0
          AND length(json_extract(canonical_target_json,'$.snapshot_sha256'))=64
          AND json_extract(canonical_target_json,'$.snapshot_sha256') NOT GLOB '*[^0-9a-f]*'
          AND json_type(canonical_target_json,'$.approval_reference')='text'
          AND length(json_extract(canonical_target_json,'$.approval_reference'))>0
          AND CASE canonical_status
            WHEN 'RESOLVED_SUBSTANCE' THEN json_extract(canonical_target_json,'$.registry_type')='Substance'
                AND substr(json_extract(canonical_target_json,'$.id'),1,4)='SUB_'
                AND length(json_extract(canonical_target_json,'$.id'))=12
            ELSE json_extract(canonical_target_json,'$.registry_type')='ChemicalConcept'
                AND substr(json_extract(canonical_target_json,'$.id'),1,3)='CC_'
                AND length(json_extract(canonical_target_json,'$.id'))=11
          END
        END, 0)),
    FOREIGN KEY(concept_id, registered_revision) REFERENCES source_revision(concept_id, fingerprint)
        DEFERRABLE INITIALLY DEFERRED
);
CREATE INDEX domain_label_lookup ON domain_concept(domain_type,label_key);
CREATE INDEX domain_status_lookup ON domain_concept(domain_type,canonical_status);

CREATE TABLE source_revision(
    concept_id TEXT NOT NULL REFERENCES domain_concept(concept_id),
    fingerprint TEXT NOT NULL CHECK(length(fingerprint)=64),
    observed_label TEXT NOT NULL,
    source_version TEXT,
    review_required INTEGER NOT NULL CHECK(review_required IN (0,1)),
    observed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY(concept_id,fingerprint)
);
CREATE TRIGGER source_revision_append_only_update BEFORE UPDATE ON source_revision
BEGIN SELECT RAISE(ABORT,'SOURCE_REVISION_APPEND_ONLY'); END;
CREATE TRIGGER source_revision_append_only_delete BEFORE DELETE ON source_revision
BEGIN SELECT RAISE(ABORT,'SOURCE_REVISION_APPEND_ONLY'); END;

CREATE TABLE assessment(
    concept_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    attempted INTEGER NOT NULL CHECK(attempted IN (0,1)),
    attributes_json TEXT NOT NULL CHECK(json_valid(attributes_json)),
    roles_json TEXT NOT NULL CHECK(json_valid(roles_json)),
    summary_json TEXT NOT NULL CHECK(json_valid(summary_json)),
    trace_json TEXT NOT NULL CHECK(json_valid(trace_json)),
    PRIMARY KEY(concept_id,revision,pipeline_version),
    FOREIGN KEY(concept_id,revision) REFERENCES source_revision(concept_id,fingerprint)
);
CREATE TABLE review_comparison(
    left_id TEXT NOT NULL,
    left_revision TEXT NOT NULL,
    right_reference TEXT NOT NULL,
    right_id TEXT,
    right_revision TEXT NOT NULL,
    pipeline_version TEXT NOT NULL,
    verdict TEXT NOT NULL CHECK(verdict IN ('EQUIVALENT','DISTINCT','UNRESOLVED')),
    comparison_json TEXT NOT NULL CHECK(json_valid(comparison_json)),
    PRIMARY KEY(left_id,left_revision,right_reference,right_revision,pipeline_version),
    FOREIGN KEY(left_id,left_revision) REFERENCES source_revision(concept_id,fingerprint),
    FOREIGN KEY(right_id,right_revision) REFERENCES source_revision(concept_id,fingerprint),
    CHECK(right_id IS NULL OR left_id<>right_id)
);
CREATE INDEX review_comparison_right ON review_comparison(right_id);
