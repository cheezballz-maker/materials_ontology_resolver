-- Additive migration. Existing identities, assertions and comparisons are retained.
CREATE TABLE source_payload(
    concept_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    content_key TEXT NOT NULL CHECK(length(content_key)=64),
    payload_json TEXT NOT NULL CHECK(json_valid(payload_json)),
    PRIMARY KEY(concept_id,revision),
    UNIQUE(concept_id,content_key),
    FOREIGN KEY(concept_id,revision) REFERENCES source_revision(concept_id,fingerprint)
);
CREATE TABLE source_head(
    concept_id TEXT PRIMARY KEY REFERENCES domain_concept(concept_id),
    observed_revision TEXT NOT NULL,
    present INTEGER NOT NULL CHECK(present IN (0,1)),
    continuity_hold INTEGER NOT NULL CHECK(continuity_hold IN (0,1)),
    FOREIGN KEY(concept_id,observed_revision) REFERENCES source_revision(concept_id,fingerprint)
);
CREATE TABLE source_review(
    event_id INTEGER PRIMARY KEY,
    concept_id TEXT NOT NULL REFERENCES domain_concept(concept_id),
    revision TEXT NOT NULL,
    event TEXT NOT NULL,
    actor TEXT NOT NULL,
    detail TEXT NOT NULL,
    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(concept_id,revision) REFERENCES source_revision(concept_id,fingerprint)
);
CREATE INDEX source_review_concept ON source_review(concept_id,event_id);
CREATE TRIGGER source_review_append_only_update BEFORE UPDATE ON source_review
BEGIN SELECT RAISE(ABORT,'SOURCE_REVIEW_APPEND_ONLY'); END;
CREATE TRIGGER source_review_append_only_delete BEFORE DELETE ON source_review
BEGIN SELECT RAISE(ABORT,'SOURCE_REVIEW_APPEND_ONLY'); END;
CREATE TRIGGER source_payload_append_only_update BEFORE UPDATE ON source_payload
BEGIN SELECT RAISE(ABORT,'SOURCE_PAYLOAD_APPEND_ONLY'); END;
CREATE TRIGGER source_payload_append_only_delete BEFORE DELETE ON source_payload
BEGIN SELECT RAISE(ABORT,'SOURCE_PAYLOAD_APPEND_ONLY'); END;
CREATE TABLE registration_run(
    run_id TEXT PRIMARY KEY,
    source_namespace TEXT NOT NULL,
    domain_type TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL,
    expected_count INTEGER NOT NULL CHECK(expected_count>=0),
    full_snapshot INTEGER NOT NULL CHECK(full_snapshot IN (0,1)),
    next_offset INTEGER NOT NULL DEFAULT 0 CHECK(next_offset BETWEEN 0 AND expected_count),
    completed INTEGER NOT NULL DEFAULT 0 CHECK(completed IN (0,1)),
    CHECK(completed=0 OR next_offset=expected_count)
);
CREATE UNIQUE INDEX registration_scope_open
    ON registration_run(source_namespace,domain_type) WHERE completed=0;
CREATE TABLE registration_member(
    run_id TEXT NOT NULL REFERENCES registration_run(run_id),
    concept_id TEXT NOT NULL,
    revision TEXT NOT NULL,
    source_version TEXT,
    PRIMARY KEY(run_id,concept_id),
    FOREIGN KEY(concept_id,revision) REFERENCES source_revision(concept_id,fingerprint)
);
CREATE INDEX assessment_stage_cache ON assessment(pipeline_version,concept_id,revision);
PRAGMA user_version=2;
