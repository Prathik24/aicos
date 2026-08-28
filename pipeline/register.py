
from pipeline.validate import _owner_str


from core.identity import commitment_key , decision_key
from core.schemas.commitment import FounderVerdict

import csv
from pathlib import Path

COLUMNS = ["id", "natural_key", "kind", "text", "owner", "due_date",
           "status", "confidence", "evidence_locations", "verdict",
           "verdict_reason"]


def apply_verdicts(report, verdicts):
    out = []
    for c in report.commitments: 
        key = commitment_key(owner = _owner_str(c.owner) , action = c.action)
        entry = verdicts.entries.get(key)
        if entry is None:
            out.append(c)
            continue 
        fv = FounderVerdict(verdict = entry.verdict , reason = entry.reason, decided_at = verdicts.decided_at)
        updates = {"status" : entry.verdict , "verdict" : fv}
        if entry.verdict == "edited":
            updates["action"] = entry.edited_text 
        out.append(c.model_copy(update = updates))


    for d in report.decisions: 
        key = decision_key(owner = _owner_str(d.owner) , statement = d.statement)
        entry = verdicts.entries.get(key)
        if entry is None: 
            out.append(d)
            continue
        fv = FounderVerdict(verdict = entry.verdict , reason = entry.reason , decided_at = verdicts.decided_at)
        updates = {"status" : entry.verdict , "verdict" : fv}
        if entry.verdict == "edited":
            updates["statement"] = entry.edited_text
        out.append(d.model_copy(update = updates))
    return out 





def _record_to_row(rec, key: str) -> dict:
    is_commitment = hasattr(rec, "action")
    return {
        "id": "",                                    # filled by caller
        "natural_key": key,
        "kind": "commitment" if is_commitment else "decision",
        "text": rec.action if is_commitment else rec.statement,
        "owner": rec.owner.raw_mention,
        "due_date": str(getattr(rec, "due_date", "") or ""),
        "status": rec.status,
        "confidence": rec.confidence,
        "evidence_locations": ";".join(ev.location for ev in rec.evidence),
        "verdict": rec.verdict.verdict if rec.verdict else "",
        "verdict_reason": (rec.verdict.reason or "") if rec.verdict else "",
    }


def write_register(records, path: str = "data/out/register.csv") -> str:
    p = Path(path)

    # CASE 1 + CASE 6: load existing state; missing file = empty ledger,
    # unreadable file = stop the line (never write over corruption).
    rows_by_key: dict[str, dict] = {}
    if p.exists():
        try:
            with open(p, newline="") as f:
                for row in csv.DictReader(f):
                    rows_by_key[row["natural_key"]] = row
        except (csv.Error, KeyError) as e:
            raise RuntimeError(f"register at {path} is unreadable: {e}") from e

    # Next-ID counters: scan existing IDs per type prefix (CASE 3 sub-answer).
    def _max_id(prefix: str) -> int:
        nums = [int(r["id"].split("-")[1]) for r in rows_by_key.values()
                if r["id"].startswith(prefix)]
        return max(nums, default=0)

    next_commit = _max_id("COMMIT") + 1
    next_decision = _max_id("DECISION") + 1

    # The fold: upsert today's records.
    for rec in records:
        if hasattr(rec, "action"):
            key = commitment_key(owner=_owner_str(rec.owner), action=rec.action)
        else:
            key = decision_key(owner=_owner_str(rec.owner), statement=rec.statement)
        new_row = _record_to_row(rec, key)

        if key in rows_by_key:
            # CASE 2: ID is write-once; every other field is last-write-wins.
            new_row["id"] = rows_by_key[key]["id"]
        else:
            # CASE 3: new key -> mint next ID for its type.
            if new_row["kind"] == "commitment":
                new_row["id"] = f"COMMIT-{next_commit:04d}"
                next_commit += 1
            else:
                new_row["id"] = f"DECISION-{next_decision:04d}"
                next_decision += 1
        rows_by_key[key] = new_row
    # CASE 4: rows for keys not in today's records were loaded and never
    # touched — history survives by construction.

    # CASE 5: sort by ID so the file's bytes depend on its contents,
    # not on extraction order. Same state -> same file, every run.
    ordered = sorted(rows_by_key.values(), key=lambda r: r["id"])

    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for row in ordered:
            w.writerow(row)
    return str(p)

    
        
    
        



