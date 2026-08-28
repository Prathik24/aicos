# scripts/day4_check.py
import sys, json
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.extract import extract
from pipeline.validate import validate
from pipeline.render import render_package
from pipeline.register import apply_verdicts, write_register
from core.schemas.extraction import ExtractionResult
from core.schemas.verdict import VerdictFile
from pipeline.followup import draft_fulfillment_email


SLICE = "data/samples/meeting_01_slice.txt"
CACHE = Path("data/out/extraction_cache.json")
VERDICTS = Path("data/out/verdicts.json")
MEETING_DATE = date(2026, 8, 5)   # TODO: derive from calendar export
SOURCE_ID = "SRC-0001"

transcript = open(SLICE).read()

# Extraction: cached so run 2 tests the REGISTER's idempotency,
# not the model's variance (known limit: variance -> key instability, TODO).
if CACHE.exists():
    print("using cached extraction")
    result = ExtractionResult.model_validate_json(CACHE.read_text())
else:
    print("extracting (slow)...")
    result = extract(transcript)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(result.model_dump_json(indent=2))

report = validate(result, transcript, MEETING_DATE, SOURCE_ID)
pkg = render_package(report, "Alex sync — Aug 5")
print(f"approval package: {pkg}")

if not VERDICTS.exists():
    print("\nNo verdicts.json yet. Open the package, review it as Alex,")
    print(f"then write {VERDICTS} and re-run this script.")
    sys.exit(0)

verdicts = VerdictFile.model_validate_json(VERDICTS.read_text())
final = apply_verdicts(report, verdicts)
out = write_register(final)

approved = [r for r in final if r.status in ("approved", "edited")]
if approved:
    path = draft_fulfillment_email(approved[0], recipient="Prathik Prasad")
    print(f"fulfillment draft: {path}")
print(f"register written: {out}")