from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

import pytest
from rdkit import rdBase

from canonical_registry.chemistry import describe
from canonical_registry.identity_sufficiency.contract import Claim, Evidence, Evaluator, WHOLE
from canonical_registry.authoritative_lookup.lookup import SourceReferent
from canonical_registry.cosing_pilot.mapping_preview import development_targets
from ..fixture import initialize, open_fixture, reader
from ..workflow import StageC
from creation_authorization import connect_creation
from creation_transaction import CreationTransactionFailure
import derived_index


def source(label, name, smiles, *, partial=False, material="UNESTABLISHED"):
    ref = "synthetic:" + label
    claims = [Claim("structure", "SMILES", smiles, WHOLE, ref, "test source",
                    ("STRUCTURE", "REFERENT"), "synthetic fixture", "typed graph", "v1")]
    if partial:
        claims.append(Claim("stereo", "STEREO_SCOPE", "EXPLICITLY_UNSPECIFIED", WHOLE, ref,
                            "test source", ("SPECIFICATION", "REFERENT"), "synthetic fixture", "stereo scope", "v1"))
    e = Evidence(label, ref, "v1", name, tuple(claims), material, ("source scope",) if material != "UNESTABLISHED" else ())
    return SourceReferent(e, "synthetic fixture", (name,), "", {})


def official(graph):
    return {"status": "SUCCESS", "agrees": True, "inchi": graph["inchi"], "inchikey": graph["inchikey"]}


def state(path):
    with closing(reader(path)) as db:
        tables = ("substance_identity", "substance_alias", "substance_identifier", "substance_structure",
                  "concept_substance_association", "stage_c_request", "substance_creation_record",
                  "concept_resolution_event", "canonical_id_sequence")
        return {t: db.execute("SELECT * FROM " + t + " ORDER BY rowid").fetchall() for t in tables}


@pytest.fixture(scope="module")
def setup(tmp_path_factory):
    from canonical_registry.authoritative_lookup.sources import file_digest
    pins = {k: {"path": str(p), "sha256": file_digest(p)} for k, p in development_targets().items()}
    path = tmp_path_factory.mktemp("stage_c") / "run"
    original = derived_index.CACHE
    test_cache = Path(original).with_name(f"stage_c_test_index_{uuid4().hex}.sqlite")
    derived_index.CACHE = test_cache
    try:
        with rdBase.BlockLogs():
            permit, concepts, metadata = initialize(path, pins)
            try:
                yield path, permit, concepts
            finally:
                # initialize places these two test clones outside pytest's tmp_path.
                name = f"stage_c_{metadata['run_id']}.sqlite"
                assert permit.path.name == concepts.path.name == name
                for clone in (permit.path, concepts.path):
                    for suffix in ("", "-wal", "-shm", "-journal"):
                        clone.with_name(name + suffix).unlink(missing_ok=True)
    finally:
        derived_index.CACHE = original
        for suffix in ("", "-wal", "-shm", "-journal"):
            test_cache.with_name(test_cache.name + suffix).unlink(missing_ok=True)


def engine(setup, validator=official):
    _, permit, concepts = setup
    return StageC(permit, concepts, Evaluator(validator), {})


def test_stage_c_reuse_water(setup):
    c = engine(setup)
    r = c.process(source("water", "Water", "O"), [], 0)
    assert r["outcome"] == "EXISTING_SUBSTANCE_REUSED"
    assert r["target"] == "SUB_00000562"


def test_stage_c_rollback_after_creation_and_checkpoint(setup):
    c = engine(setup)
    before = state(c.permit.path)

    def interrupt(phase):
        if phase == "BEFORE_COMMIT":
            raise RuntimeError("TEST_ROLLBACK_AFTER_STAGE_C_CHECKPOINT")

    with pytest.raises(CreationTransactionFailure, match="TEST_ROLLBACK"):
        c.process(source("rollback", "Distinct control", "[13CH3]CO"), [], 0, failure_injector=interrupt)
    assert state(c.permit.path) == before


def test_distinct_isotope_and_concurrent_same_identity(setup):
    baseline = state(setup[1].path)
    natural = engine(setup).process(source("natural", "Pentane", "CCCCC"), [], 0)
    labelled = "[13CH3]CCCC"

    def process(ref):
        return engine(setup).process(source(ref, "13C pentane", labelled), [], 0)

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = list(pool.map(process, ["isotope_1", "isotope_2"]))
    assert {first["outcome"], second["outcome"]} == {"NEW_SUBSTANCE_CREATED", "EXISTING_SUBSTANCE_REUSED"}
    assert first["target"] == second["target"] != natural["target"]
    after = state(setup[1].path)
    assert len(after["substance_creation_record"]) - len(baseline["substance_creation_record"]) in (1, 2)
    permit, concepts, _ = open_fixture(setup[0])
    restarted = StageC(permit, concepts, Evaluator(official), {})
    replay = restarted.process(source("isotope_1", "13C pentane", labelled), [], 0)
    assert replay["checkpoint_replay"] and replay["target"] == first["target"]
    with pytest.raises(ValueError, match="EVIDENCE_CHANGED"):
        restarted.process(source("isotope_1", "Pentane", "CCCCC"), [], 0)
    assert after == state(setup[1].path)


def test_broad_or_unvalidated_cannot_write_identity(setup):
    c = engine(setup, lambda g: {**official(g), "agrees": False})
    for ref, scope in (("broad", "PREPARATION"), ("failed_official", "UNESTABLISHED")):
        actual = c.process(source(ref, "Unresolved control", "CCO", material=scope), [], 0)
        assert actual["status"] == "UNRESOLVED"
        assert "target" not in actual


def test_partial_policy_uses_existing_concept_transaction(setup):
    c = engine(setup)
    graph = "CC(O)CCC"
    result = c.process(source("partial", graph, graph, partial=True), [], 0)
    assert result["status"] == "RESOLVED_CHEMICAL_CONCEPT"
    assert c.concepts.get(result["target"])["definition"]["smiles"] == describe(graph)["smiles"]


def test_source_registry_cannot_be_opened_as_stage_c_fixture(setup):
    permit = setup[1]
    target = development_targets()["Substance"]
    forged = replace(permit, association=replace(permit.association, path=target))
    with pytest.raises(PermissionError):
        connect_creation(forged)
