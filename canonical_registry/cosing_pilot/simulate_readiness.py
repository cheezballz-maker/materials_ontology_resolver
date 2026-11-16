"""Exercise snapshot changes and an approved-mapping hold in a disposable fixture."""

import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID

from .cosing_source import observation
from .readiness import register
from .registry import canonical
from .staged_assessment import assess
from .staged_registry import StagedRegistry


def simulate(registry):
    def record(i, label, **claims):
        return observation({"inci_id":str(UUID(int=i)), "inci":label, "alias_count":0, **claims})

    original = record(1,"QUERCUS SALICINA LEAF EXTRACT")
    revised = record(1,"QUERCUS SALICINA LEAF PREPARATION",description="Fixture evidence changed")
    disappearing = record(2,"Test preparation")
    rekey = record(3,"Test preparation")
    new = record(4,"POLYQUATERNIUM-62")
    registry.initialize()
    initial = register(registry,[original,disappearing],"initial",complete_count=2)
    unchanged = register(registry,[disappearing,original],"unchanged",complete_count=2)
    assert unchanged["created"] == unchanged["new_revisions"] == 0
    initial_assessment = assess(registry,"interpret",batch="initial",typed_only=True)
    assert initial_assessment["counts"] == {"assessed":2}

    # This row is an explicitly fabricated historical approval in the fixture.
    target = {"id":"SUB_00000001","registry_type":"Substance","registry_key":"synthetic-only",
              "snapshot_sha256":"a"*64,"approval_reference":"SYNTHETIC_FIXTURE"}
    with registry.writer() as db:
        db.execute("""UPDATE domain_concept SET canonical_status='RESOLVED_SUBSTANCE',
                      canonical_target_json=? WHERE concept_id='CIC_00000001'""",(canonical(target),))
    changed_snapshot = [revised,rekey,new]
    checkpoint = register(registry,changed_snapshot,"changed",complete_count=3,batch_size=1,max_batches=1)

    def stop(offset):
        raise KeyboardInterrupt

    try:
        register(registry,changed_snapshot,"changed",complete_count=3,batch_size=1,batch_hook=stop)
    except KeyboardInterrupt:
        pass
    else:
        raise AssertionError("Fault did not reach the transaction")
    queue_interrupted = registry.source_queue()
    assert len(queue_interrupted) == 1
    resumed = register(registry,changed_snapshot,"changed",complete_count=3,batch_size=1)
    assert resumed["created"] == 2 and resumed["missing"] == 1
    queue_resumed = registry.source_queue()
    assert len(queue_resumed) == 3
    new_interpretation = assess(registry,"interpret",batch="changed",typed_only=True)
    assert new_interpretation["counts"] == {"source_held_or_payload_unavailable":2,"assessed":1}
    pending_interpretation = assess(registry,"interpret",source_ids=[revised.source_reference],pending=True,typed_only=True)
    assert pending_interpretation["counts"] == {"assessed":1}
    blocked_resolution = assess(registry,"resolve",source_ids=[revised.source_reference],typed_only=True)
    assert blocked_resolution["counts"] == {"source_held_or_payload_unavailable":1}
    assert registry.detail("CIC_00000001")["canonical_target"] == target
    assert registry.detail("CIC_00000001")["current_mapping_applicability"] == "PENDING_SOURCE_REVIEW"
    try:
        registry.review_source("CIC_00000001",revised.content_key,action="adopt",actor="Fixture reviewer",note="Test")
    except ValueError as error:
        approval_block = str(error)
    else:
        raise AssertionError("Approved mapping revision must stay held")
    registry.review_source("CIC_00000001",revised.content_key,action="defer",actor="Fixture reviewer",
                           note="Identity and mapping review remain pending")
    original_returned = register(registry,[original],"return")
    returned_detail = registry.detail("CIC_00000001")
    assert returned_detail["current_mapping_applicability"] == "PENDING_SOURCE_REVIEW"
    with registry.reader() as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert not db.execute("PRAGMA foreign_key_check").fetchall()
    return {"fixture":"synthetic","initial":initial,"unchanged":unchanged,"checkpoint":checkpoint,
            "queue_after_rollback":queue_interrupted,"resumed":resumed,"queue_after_resume":queue_resumed,
            "initial_interpretation":initial_assessment,"selective_interpretation":new_interpretation,
            "pending_interpretation":pending_interpretation,"blocked_resolution":blocked_resolution,
            "approved_revision_adoption_block":approval_block,"prior_source_evidence_returned":original_returned,
            "approved_mapping_applicability_after_return":returned_detail["current_mapping_applicability"],
            "retained_approval":returned_detail["canonical_target"],"review_history":returned_detail["source_review"],
            "integrity":"PASS"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",required=True,type=Path)
    args = parser.parse_args()
    with TemporaryDirectory(dir=Path(__file__).parent) as directory:
        result = simulate(StagedRegistry(Path(directory)/"simulation.sqlite"))
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")


if __name__ == "__main__":
    main()
