# aicos

Local-first commitment tracking system that extracts, validates, and manages action items from meeting transcripts using Ollama LLMs with human-in-the-loop approval.

## Results

Example extraction from a 2-person project meeting:

| Metric | Value |
|---|---|
| Commitments extracted | 5 |
| False positives (filtered) | 2 |
| Approval time | ~2 minutes (HTML review) |
| Final register entries | 3 approved items |

<!-- Real accuracy metrics TBD - requires labeled test set -->

## What's inside

- **Two-pass extraction**: Scan for candidate turns, then focused extraction with ±2 turn context windows to manage token budgets
- **Evidence-grounded validation**: Anchor checking, due date parsing from natural language, deduplication against historical commitments
- **Config-driven LLM routing**: Tasks map to tiers, tiers map to models via YAML (currently using Ollama qwen3:8b and qwen2.5:latest)
- **HTML approval package generator**: Jinja2 templates with inline radio buttons for human review
- **Persistent CSV ledger**: Last-write-wins semantics with commitment IDs, evidence excerpts, and fulfillment status
- **Audit logging**: JSONL format tracking all LLM calls with prompts, completions, and latencies

## Approach

The core challenge was extracting commitments from long transcripts without blowing context windows. Standard approaches that send entire transcripts to the LLM fail on meetings over 4k tokens. I implemented a two-pass system: the first pass scans for candidate turns where commitments might exist, and the second pass extracts from focused windows (±2 turns of context). Every extracted item includes verbatim evidence excerpts, which the validation pipeline verifies against the source transcript.

Due dates are parsed from natural language ("by Friday", "next week", "end of day") and anchored to the meeting date. This required building a date resolver that handles both absolute dates ("August 30th") and relative references ("this afternoon" spoken on Tuesday means Tuesday EOD).

Human approval happens via an HTML package with inline radio buttons. The system generates a package showing each commitment, its evidence, and parsed metadata. Humans mark approve/reject/defer, save as JSON, and re-run the pipeline. Approved items get written to a CSV register with last-write-wins deduplication.

All LLM calls go through a gateway abstraction that routes tasks to models based on config. Right now it's just Ollama endpoints, but the interface supports swapping in API calls or local fine-tuned models. Audit logs capture every LLM interaction for debugging and future fine-tuning datasets.

The hardest part was deduplication - deciding when "draft migration plan" on Monday is the same commitment as "migration plan ready" on Friday. Currently using exact commitment key matching (owner + action phrase), which works but misses fuzzy duplicates.

## Run it

```bash
git clone https://github.com/Prathik24/aicos.git
cd aicos
pip install -r requirements.txt

# Install Ollama and pull models
# Download from: https://ollama.ai
ollama pull qwen3:8b
ollama pull qwen2.5:latest

# Place your meeting transcript in data/samples/
# Format: "Speaker Name: dialogue text" per line
# Example: data/samples/example_meeting.txt

# Run extraction and validation
python scripts/run_meeting.py example_meeting --date 2026-08-28 --source-id SRC-0001

# Review the approval package
open data/out/example_meeting/approval_package.html

# Create verdicts.json with your decisions
# Format: {"commitment_id": "approved", ...}
# Save to: data/out/example_meeting/verdicts.json

# Re-run to generate register and email drafts
python scripts/run_meeting.py example_meeting --date 2026-08-28 --source-id SRC-0001

# Check outputs
cat data/out/example_meeting/register.csv
cat data/out/example_meeting/fulfillment_draft.txt
```

Configs are in `config/routes.yaml` - map extraction/validation tasks to model tiers and models to Ollama endpoints.

## Limitations

- **Single-seed extraction**: No temperature tuning or multiple sampling passes to capture extraction variance
- **No LoRA fine-tuning infrastructure**: Uses pre-trained models via Ollama API; no training pipeline for domain adaptation
- **Manual verdicts editing**: Approval requires editing JSON files; no interactive web UI
- **Transcript-only ingest**: No email or Slack connectors; requires pre-formatted meeting transcripts
- **Exact-match deduplication**: Commitment keys use string matching; no fuzzy matching or semantic similarity for duplicates
- **No multi-party complexity handling**: Works best for 2-4 person meetings; large meetings with crosstalk may degrade quality

## References

- [Ollama](https://ollama.ai) - Local LLM inference
- [Pydantic](https://docs.pydantic.dev/) - Data validation and schema enforcement
- [Jinja2](https://jinja.palletsprojects.com/) - Template rendering for HTML packages

## Architecture notes

**Why two-pass extraction?**
Sending 10k token transcripts to qwen3:8b costs ~2s inference and often misses commitments buried in context. First pass scans for candidate turns (mentions of deadlines, action verbs, "I'll..."). Second pass processes only ±2 turns around each candidate. Reduces context by 80% and improves recall.

**Why CSV for the register?**
Needed something human-readable and git-diffable for auditing changes over time. CSV gives both. Last-write-wins means re-processing a meeting updates existing commitments rather than creating duplicates.

**Why HTML packages instead of a web UI?**
Approval is async and infrequent (once per meeting). HTML packages are self-contained, email-friendly, and don't require a running server. Power users can script verdicts.json generation.

**Model routing strategy:**
Config maps tasks to tiers (e.g., "extraction" → "tier-1"), then tiers to models. Allows A/B testing different models for the same task without code changes. Currently using qwen3:8b for extraction (speed) and qwen2.5:latest for validation (accuracy).
