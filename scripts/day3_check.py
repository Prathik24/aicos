# scripts/day3_check.py
import sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.extract import extract, extract_two_pass

SLICE = "data/samples/meeting_01_slice.txt"
transcript = open(SLICE).read()

turns = {line.split("]")[0].lstrip("[").split(" ")[0]: line
         for line in transcript.splitlines() if line.startswith("[T-")}


def report(label: str, result, seconds: float):
    print(f"\n{'='*20} {label}  ({seconds:.0f}s) {'='*20}")
    print(f"COMMITMENTS ({len(result.commitments)})")
    for c in result.commitments:
        print(f"  [{c.evidence[0].location}] {c.action}")
        print(f"      owner: {c.owner.raw_mention} | due: {c.due_text} | conf: {c.confidence}")
    print(f"DECISIONS ({len(result.decisions)})")
    for d in result.decisions:
        print(f"  [{d.evidence[0].location}] {d.statement} | conf: {d.confidence}")
    print(f"KEY FACTS ({len(result.key_facts)})")
    for k in result.key_facts:
        print(f"  [{k.evidence[0].location}] {k.statement} | conf: {k.confidence}")
    print("ANCHORS")
    for item in (list(result.commitments) + list(result.decisions)
                 + list(result.key_facts)):
        for ev in item.evidence:
            ok = ev.excerpt in turns.get(ev.location, "")
            print(f"  [{ev.location}] {'OK' if ok else 'FABRICATED/PARAPHRASED'}")


print(f"Input: {SLICE} — {len(transcript.splitlines())} turns")

t0 = time.monotonic()
r1 = extract(transcript)                 # PATH A: single-pass v5
report("SINGLE-PASS (v5)", r1, time.monotonic() - t0)

t0 = time.monotonic()
r2 = extract_two_pass(transcript)        # PATH B: scan + windows
report("TWO-PASS (scan v1 + window v1)", r2, time.monotonic() - t0)