import pathlib
from core.schemas.commitment import Commitment
from core.schemas.decision import Decision
import pytest
from pydantic import ValidationError
from core.schemas.extraction import ExtractionResult

def test_valid_fixture_parses():
    raw = pathlib.Path("tests/fixtures/commitment_good.json").read_text()
    c = Commitment.model_validate_json(raw)
    assert c.status == "proposed"
    assert c.owner.kind == "resolved"
    assert c.owner.entity_id == "PERSON-0001"

def test_bad_fixture_rejected():
    raw = pathlib.Path("tests/fixtures/commitment_bad.json").read_text()
    with pytest.raises(ValidationError):
        Commitment.model_validate_json(raw)

def test_approved_requires_verdict():
    with pytest.raises(ValidationError) as exc_info:
        Commitment(
            action="test",
            owner={"kind": "unresolved", "raw_mention": "Alex"},
            evidence=[{"source_id": "SRC-0001", "source_type": "transcript",
                       "location": "00:00:01", "excerpt": "test"}],
            confidence=0.5,
            status="approved",
        )
    assert "verdict" in str(exc_info.value)

def test_decision():
    raw = pathlib.Path("tests/fixtures/decision_good.json").read_text()
    d = Decision.model_validate_json(raw)
    d.status = "approved"



def test_extraction_rejects_resolved_owner():
    with pytest.raises(ValidationError):
        ExtractionResult(
            commitments=[{
                "action": "test",
                "owner": {"kind": "resolved", "entity_id": "PERSON-0001"},
                "evidence": [{"source_id": "SRC-0001", "source_type": "transcript",
                              "location": "00:00:01", "excerpt": "test"}],
                "confidence": 0.5,
            }],
            decisions=[],
        )