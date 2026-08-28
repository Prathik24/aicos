# scripts/day3b_check.py
import sys, time
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.extract import extract
from pipeline.validate import validate

SLICE = "data/samples/meeting_01_slice.txt"
MEETING_DATE = date(2026, 8, 5)   # TODO: derive from the calendar export at ingest
SOURCE_ID = "SRC-0001"

transcript = open(SLICE).read()
print(f"Input: {SLICE} — {len(transcript.splitlines())} turns")

t0 = time.monotonic()
result = extract(transcript)
print(f"extract: {time.monotonic() - t0:.0f}s")

t0 = time.monotonic()
report = validate(result, transcript, MEETING_DATE, SOURCE_ID)
print(f"validate: {time.monotonic() - t0:.2f}s\n")   # should be ~0 — it's pure code

print(f"=== COMMITMENTS ({len(report.commitments)}) ===")
for c in report.commitments:
    print(f"[{c.evidence[0].location}] {c.action}")
    print(f"    owner: {c.owner.raw_mention} | due_text: {c.due_text} "
          f"| due_date: {c.due_date} | conf: {c.confidence}")
    print(f"    status: {c.status} | evidence entries: {len(c.evidence)}")

print(f"\n=== DECISIONS ({len(report.decisions)}) ===")
for d in report.decisions:
    print(f"[{d.evidence[0].location}] {d.statement} | conf: {d.confidence}")

print(f"\n=== KEY FACTS ({len(report.key_facts)}) ===")
for k in report.key_facts:
    print(f"[{k.evidence[0].location}] {k.statement} | conf: {k.confidence}")

print(f"\n=== FLAGS ({len(report.flags)}) ===")
if not report.flags:
    print("(none — all checks passed)")
for f in report.flags:
    print(f"[{f.rule}] {f.detail}")
    print(f"    record: {f.record_key}")