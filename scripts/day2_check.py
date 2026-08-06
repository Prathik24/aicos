# scripts/day2_check.py
import sys                                                                                                 
from pathlib import Path                                                                                   
sys.path.insert(0, str(Path(__file__).parent.parent))                                                      
                                                                                                            
from pipeline.extract import extract   


SLICE = "data/samples/meeting_01_slice.txt"

transcript = open(SLICE).read()
print(f"Input: {SLICE} — {len(transcript.splitlines())} turns, "
      f"{len(transcript)} chars\nExtracting (may take 1–3 min on 8B)...\n")

result = extract(transcript)

print(f"=== COMMITMENTS ({len(result.commitments)}) ===")
for c in result.commitments:
    ev = c.evidence[0]
    print(f"[{ev.location}] {c.action}")
    print(f"    owner: {c.owner.raw_mention} | due: {c.due_text} | conf: {c.confidence}")
    print(f"    excerpt: \"{ev.excerpt[:90]}\"")

print(f"\n=== DECISIONS ({len(result.decisions)}) ===")
for d in result.decisions:
    ev = d.evidence[0]
    print(f"[{ev.location}] {d.statement}")
    print(f"    owner: {d.owner.raw_mention} | conf: {d.confidence}")
    print(f"    excerpt: \"{ev.excerpt[:90]}\"")

# Anchor verification: does each cited turn actually contain its excerpt?
print("\n=== ANCHOR CHECK ===")
turns = {line.split("]")[0].lstrip("[").split(" ")[0]: line
         for line in transcript.splitlines() if line.startswith("[T-")}
for item in list(result.commitments) + list(result.decisions):
    for ev in item.evidence:
        turn_line = turns.get(ev.location, "")
        verdict = "OK" if ev.excerpt in turn_line else "FABRICATED/PARAPHRASED"
        print(f"[{ev.location}] {verdict}")


print(f"\n=== KEY FACTS ({len(result.key_facts)}) ===")
for k in result.key_facts:
    ev = k.evidence[0]
    print(f"[{ev.location}] {k.statement}")
    print(f"    conf: {k.confidence}")
    print(f"    excerpt: \"{ev.excerpt[:90]}\"")

# Anchor verification: does each cited turn actually contain its excerpt?
print("\n=== ANCHOR CHECK ===")
turns = {line.split("]")[0].lstrip("[").split(" ")[0]: line
         for line in transcript.splitlines() if line.startswith("[T-")}
for item in (list(result.commitments) + list(result.decisions)
             + list(result.key_facts)):
    for ev in item.evidence:
        turn_line = turns.get(ev.location, "")
        verdict = "OK" if ev.excerpt in turn_line else "FABRICATED/PARAPHRASED"
        print(f"[{ev.location}] {verdict}")