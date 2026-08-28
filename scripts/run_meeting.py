# scripts/run_meeting.py
import sys, argparse
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.ingest import number_turns
from pipeline.extract import extract
from pipeline.validate import validate
from pipeline.render import render_package
from pipeline.register import apply_verdicts, write_register
from core.schemas.extraction import ExtractionResult
from core.schemas.verdict import VerdictFile
from pipeline.followup import draft_fulfillment_email
from core.identity import commitment_key
from pipeline.validate import _owner_str


USER_NAME = "User"


p = argparse.ArgumentParser()
p.add_argument("meeting")                      # e.g. meeting_02
p.add_argument("--date", required=True)        # e.g. 2026-08-10
p.add_argument("--source-id", required=True)   # e.g. SRC-0002
args = p.parse_args()

raw_path = Path(f"data/samples/{args.meeting}.txt")
out_dir = Path(f"data/out/{args.meeting}")     # per-meeting scratch — the trap killer
out_dir.mkdir(parents=True, exist_ok=True)
cache, verdicts_path = out_dir / "extraction_cache.json", out_dir / "verdicts.json"

transcript = number_turns(raw_path.read_text())
(out_dir / "numbered.txt").write_text(transcript)

if cache.exists():
    result = ExtractionResult.model_validate_json(cache.read_text())
else:
    result = extract(transcript)
    cache.write_text(result.model_dump_json(indent=2))

meeting_date = date.fromisoformat(args.date)
report = validate(result, transcript, meeting_date, args.source_id)
pkg = render_package(report, args.meeting, out_path=str(out_dir / "package.html"))
print(f"package: {pkg}")

if not verdicts_path.exists():
    print(f"review the package, then write {verdicts_path} and re-run")
    sys.exit(0)

final = apply_verdicts(report, VerdictFile.model_validate_json(verdicts_path.read_text()))
print(f"register: {write_register(final)}")     # shared ledger, deliberately


drafted = 0
for rec in final:
    if rec.status not in ("approved", "edited"):
        continue
    if not hasattr(rec, "action"):          # commitments only, not decisions
        continue
    if rec.owner.raw_mention != USER_NAME:  # fulfillment = my own promises
        print(f"skipped (owner {rec.owner.raw_mention}): {rec.action[:60]}")
        continue
    out = out_dir / f"draft_{commitment_key(owner=_owner_str(rec.owner), action=rec.action)[:8]}.txt"
    path = draft_fulfillment_email(rec, recipient="Alex Vetsak",
                                   out_path=str(out))
    drafted += 1
    print(f"draft: {path}")
print(f"{drafted} fulfillment draft(s)")