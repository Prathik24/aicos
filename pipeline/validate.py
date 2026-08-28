




from core.schemas.commitment import Commitment
from core.schemas.decision import Decision
from core.schemas.evidence import SourceEvidence
from core.schemas.extraction import CandidateCommitment, CandidateDecision, ExtractionResult
import re
import calendar
from datetime import date, datetime, time, timedelta
from dateutil import parser as dateutil_parser

from core.schemas.validation import ValidationReport
from datetime import date
from core.schemas.extraction import ExtractionResult
from core.schemas.validation import ValidationReport, Flag
from core.identity import commitment_key, decision_key, key_fact_key



def _to_commitment(cand: CandidateCommitment, source_id: str) -> Commitment:
    evidence = [
        SourceEvidence(
            source_id=source_id,
            source_type="transcript",   # MVP: pipeline only ingests transcripts;
                                        # becomes a parameter when email ingest arrives
            location=ev.location,
            excerpt=ev.excerpt,
        )
        for ev in cand.evidence
    ]
    return Commitment(
        action=cand.action,
        owner=cand.owner,               # UnresolvedOwner passes through untouched —
                                        # resolution is Resolve's job, not ours
        evidence=evidence,
        due_text=cand.due_text,
        due_date=None,                  # parser (sub-step 3) is the only writer
        confidence=cand.confidence,
        status="proposed",
    )


def _to_decision(cand: CandidateDecision, source_id: str) -> Decision:
    evidence = [
        SourceEvidence(
            source_id=source_id,
            source_type="transcript",   # MVP: pipeline only ingests transcripts;
                                        # becomes a parameter when email ingest arrives
            location=ev.location,
            excerpt=ev.excerpt,
        )
        for ev in cand.evidence
    ]
    return Decision(
        statement=cand.statement,
        owner=cand.owner,               # UnresolvedOwner passes through untouched —
                                        # resolution is Resolve's job, not ours
        rationale=cand.rationale,
        evidence=evidence,  
        confidence=cand.confidence,
        status="proposed",
    )

def _to_evidence(cand: CandidateCommitment, source_id: str) -> list[SourceEvidence]:
    return [
        SourceEvidence(
            source_id=source_id,
            source_type="transcript",   # MVP: pipeline only ingests transcripts;
                                        # becomes a parameter when email ingest arrives
            location=ev.location,
            excerpt=ev.excerpt,
        )
        for ev in cand.evidence
    ]




_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday",
             "saturday", "sunday"]
_WEEKDAY_RE = re.compile(r"\b(" + "|".join(_WEEKDAYS) + r")\b", re.I)
_MONTHS_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b", re.I)


def _parse_due(due_text: str | None, meeting_date: date) -> date | None:
    """FR-07: the ONLY writer of due_date. Deterministic; anchored on
    meeting_date so re-runs are reproducible. Returns None rather than guess."""
    if not due_text:                       # handles None and ""
        return None
    text = due_text.strip().lower()

    # ---- Layer 1: relative patterns, anchored on meeting_date ----
    m = _WEEKDAY_RE.search(text)
    if m:
        target = _WEEKDAYS.index(m.group(1).lower())
        delta = (target - meeting_date.weekday()) % 7
        if delta == 0:
            delta = 7   # "by Friday" said ON a Friday -> next week's Friday
        return meeting_date + timedelta(days=delta)

    if "tomorrow" in text:
        return meeting_date + timedelta(days=1)

    if "next week" in text:
        return meeting_date + timedelta(days=7)   # convention: same day +7

    if re.search(r"end of (the )?month", text):
        last = calendar.monthrange(meeting_date.year, meeting_date.month)[1]
        return date(meeting_date.year, meeting_date.month, last)

    # ---- Layer 2: guarded absolute parsing ----
    if _looks_calendar_ish(text):
        try:
            dt = dateutil_parser.parse(
                text, fuzzy=True,
                default=datetime.combine(meeting_date, time()))
            return dt.date()
        except (ValueError, OverflowError):
            pass

     # ---- Layer 3: refuse to guess ----
    return None


_ORDINAL_DIGIT = re.compile(r"\b\d{1,2}(st|nd|rd|th)\b", re.I)
_DIGIT_NEAR_MONTH = re.compile(
    r"(\b\d{1,2}\b[^,.\n]{0,15}" + _MONTHS_RE.pattern + r")|("
    + _MONTHS_RE.pattern + r"[^,.\n]{0,15}\b\d{1,2}\b)", re.I)
_SLASH_DATE = re.compile(r"\b\d{1,2}[/-]\d{1,2}([/-]\d{2,4})?\b")


def _looks_calendar_ish(text: str) -> bool:
    """Gate for dateutil (FR-07: refuse false precision).
    Calendar-ish = digit near a month name, OR ordinal digit ('17th'),
    OR slash/dash date. Bare digits ('the 3 documents') and bare month
    names ('sometime in August') are NOT sufficient — the latter by
    deliberate choice: a month without a day would parse to a fake
    specific date via dateutil's default."""
    return bool(
        _DIGIT_NEAR_MONTH.search(text)
        or _ORDINAL_DIGIT.search(text)
        or _SLASH_DATE.search(text)
    )




def _owner_str(owner) -> str:
    # UnresolvedOwner today; entity_id when Resolve exists (kind == "resolved")
    return owner.raw_mention if owner.kind == "unresolved" else owner.entity_id


def _turns_index(transcript: str) -> dict[str, str]:
    return {line.split("]")[0].lstrip("[").split(" ")[0]: line
            for line in transcript.splitlines() if line.startswith("[T-")}


def validate(result: ExtractionResult, transcript: str,
             meeting_date: date, source_id: str) -> ValidationReport:
    flags: list[Flag] = []
    turns = _turns_index(transcript)

    # ---- Phase 1: convert ----
    commitments = [_to_commitment(c, source_id) for c in result.commitments]
    decisions   = [_to_decision(d, source_id) for d in result.decisions]
    key_facts   = list(result.key_facts)

    # ---- Phase 2: parse dues (+ due_unparseable) ----
    dated = []
    for c in commitments:
        key = commitment_key(owner=_owner_str(c.owner), action=c.action)
        parsed = _parse_due(c.due_text, meeting_date)
        if c.due_text and parsed is None:
            flags.append(Flag(record_key=key, rule="due_unparseable",
                              detail=f"could not parse due_text: '{c.due_text}'"))
        dated.append(c.model_copy(update={"due_date": parsed}))
    commitments = dated

    # ---- Phase 3: rule 1 — date in action without due ----
    for c in commitments:
        if _looks_calendar_ish(c.action) and c.due_date is None:
            # YOU: append the date_in_action_without_due flag.
            # detail should quote the action so Alex sees the suspect text.
            date_in_action_flag = Flag(record_key=commitment_key(owner=_owner_str(c.owner), action=c.action),
                                       rule="date_in_action_without_due",
                                       detail=f"action contains date-like text but due_date is None: '{c.action}'")
            flags.append(date_in_action_flag)

    # ---- Phase 4: rule 2 — anchor verification ----
    for rec, key in _records_with_keys(commitments, decisions, key_facts):
        for ev in rec.evidence:
            if ev.excerpt not in turns.get(ev.location, ""):
                # YOU: append the anchor_failed flag; detail names the location.
                anchor_failed_flag = Flag(record_key=key, rule="anchor_failed",
                                          detail=f"excerpt not found in turn '{ev.location}': '{ev.excerpt}'")
                flags.append(anchor_failed_flag)

    # ---- Phase 5: dedup by natural key ----
    commitments, merge_flags = _dedupe_by_key(
        commitments, lambda c: commitment_key(owner=_owner_str(c.owner),
                                              action=c.action))
    flags += merge_flags
    # YOU: same two lines for decisions (decision_key on statement)
    #      and key_facts (key_fact_key on statement).
    decisions, merge_flags = _dedupe_by_key(
        decisions, lambda d: decision_key(owner=_owner_str(d.owner),
                                          statement=d.statement))
    flags += merge_flags
    key_facts, merge_flags = _dedupe_by_key(
        key_facts, lambda k: key_fact_key(statement=k.statement))
    flags += merge_flags

    return ValidationReport(commitments=commitments, decisions=decisions,
                            key_facts=key_facts, flags=flags)


def _records_with_keys(commitments, decisions, key_facts):
    """Yield (record, natural_key) across all three collections."""
    for c in commitments:
        yield c, commitment_key(owner=_owner_str(c.owner), action=c.action)
    # YOU: yield decisions and key_facts with their key functions.
    # (key facts have no owner — key_fact_key takes statement only.)
    for d in decisions:
        yield d, decision_key(owner=_owner_str(d.owner), statement=d.statement)
    for k in key_facts:
        yield k, key_fact_key(statement=k.statement)    


def _dedupe_by_key(records, keyfn):
    """First-wins merge: colliding records fold their evidence into the
    survivor; each merge emits a duplicate_merged flag (visible-merge ruling)."""
    seen: dict[str, object] = {}
    flags: list[Flag] = []
    for rec in records:
        k = keyfn(rec)
        if k in seen:
            survivor = seen[k]
            merged = list(survivor.evidence) + list(rec.evidence)
            seen[k] = survivor.model_copy(update={"evidence": merged})
            flags.append(Flag(record_key=k, rule="duplicate_merged",
                              detail=f"merged duplicate; evidence now "
                                     f"{len(merged)} entries"))
        else:
            seen[k] = rec
    return list(seen.values()), flags

    
