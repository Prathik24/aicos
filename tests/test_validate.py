from pipeline.validate import _to_commitment , _to_decision, validate
from core.schemas.extraction import CandidateCommitment, CandidateDecision, ExtractionResult

from datetime import date
from pipeline.validate import _parse_due

MEETING = date(2026, 8, 5)   # a Wednesday

def test_conversion_attaches_source_and_status():
    cand = CandidateCommitment(
        action="Send Sam the scope document",
        owner={"kind": "unresolved", "raw_mention": "Jo Park"},
        evidence=[{"location": "T-0002", "excerpt": "I'll send you the scope document"}],
        confidence=0.9,
    )
    c = _to_commitment(cand, source_id="SRC-0001")
    assert c.evidence[0].source_id == "SRC-0001"
    assert c.evidence[0].source_type == "transcript"
    assert c.status == "proposed"
    assert c.commitment_id is None


def test_decision_conversion_attaches_source_and_status():
    cand = CandidateDecision(
        statement="We will proceed with the project",
        owner={"kind": "unresolved", "raw_mention": "Jo Park"},
        rationale="Budget was approved last week",
        evidence=[{"location": "T-0003", "excerpt": "We will proceed with the project"}],
        confidence=0.95,
    )
    d = _to_decision(cand, source_id="SRC-0002")
    assert d.evidence[0].source_id == "SRC-0002"
    assert d.status == "proposed"
    assert d.rationale == "Budget was approved last week"
    assert d.decision_id is None



def test_relative_weekday():
    assert _parse_due("by Friday", MEETING) == date(2026, 8, 7)

def test_absolute_date():
    assert _parse_due("17th of August", MEETING) == date(2026, 8, 17)

def test_end_of_month():
    assert _parse_due("end of the month", MEETING) == date(2026, 8, 31)

def test_unparseable_returns_none():
    assert _parse_due("soon", MEETING) is None

def test_dateutil_trap_not_triggered():
    # fuzzy dateutil would read "3" as day-of-month -> Aug 3. Must be None.
    assert _parse_due("the 3 documents", MEETING) is None

def test_none_input():
    assert _parse_due(None, MEETING) is None   # due_text is Optional — handle it


def test_validate_acceptance():
    FAKE_TRANSCRIPT = (
        "[T-0001 @00:01:00] Jo Park: I'll send the scope document by Friday\n"
        "[T-0002 @00:02:00] Sam Lee: I'll book the venue"
    )
    MEETING = date(2026, 8, 5)   # Wednesday
    result = ExtractionResult(
        commitments=[
            # 1. clean: parses to Fri Aug 7, triggers nothing
            CandidateCommitment(
                action="Send Sam the scope document",
                owner={"kind": "unresolved", "raw_mention": "Jo Park"},
                due_text="by Friday",
                evidence=[{"location": "T-0001",
                           "excerpt": "I'll send the scope document by Friday"}],
                confidence=0.9,
            ),
            # 2. conflated: date-shaped action, no due -> rule 1 only
            CandidateCommitment(
                action="Deliver the report on the 17th of August",
                owner={"kind": "unresolved", "raw_mention": "Sam Lee"},
                due_text=None,
                evidence=[{"location": "T-0002",
                           "excerpt": "I'll book the venue"}],
                confidence=0.8,
            ),
            # 3. duplicate of #1: same owner+action, different real fragment
            CandidateCommitment(
                action="send sam the scope document.",
                owner={"kind": "unresolved", "raw_mention": "jo park"},
                due_text="by Friday",
                evidence=[{"location": "T-0001",
                           "excerpt": "the scope document by Friday"}],
                confidence=0.7,
            ),
            # 4. bad anchor: excerpt exists nowhere in the transcript
            CandidateCommitment(
                action="Review the safety plan",
                owner={"kind": "unresolved", "raw_mention": "Sam Lee"},
                due_text=None,
                evidence=[{"location": "T-0001",
                           "excerpt": "words that appear nowhere"}],
                confidence=0.6,
            ),
        ],
        decisions=[], key_facts=[],
    )
    report = validate(result, FAKE_TRANSCRIPT, MEETING, "SRC-0001")

    rules = {f.rule for f in report.flags}
    assert rules == {"date_in_action_without_due", "anchor_failed",
                     "duplicate_merged"}
    clean = [c for c in report.commitments if c.due_text == "by Friday"][0]
    assert clean.due_date == date(2026, 8, 7)
    assert len(clean.evidence) == 2          # the merge folded the duplicate in