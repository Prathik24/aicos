# pipeline/extract.py
from core.schemas.extraction import ExtractionResult, ScanResult
from gateway.gateway import complete

WINDOW = 2  # turns of context each side
PROMPT_VERSION = "v2"

EXTRACTION_PROMPT = """You are an extraction system for meeting transcripts. Your job is to identify COMMITMENTS and DECISIONS from the numbered transcript below and return them as JSON matching the required schema. Extract only what the transcript supports — never infer, never invent.

A COMMITMENT is a promise or accepted request to perform a specific action. It requires: (a) a speaker taking ownership ("I'll...", "I can...", "I will send you..."), (b) a concrete deliverable or action, (c) directed at someone or something specific.

A DECISION is a resolution the speakers actually reached in this meeting — a choice made, not a plan discussed. "Let's go with X" is a decision. "We'll know in three months" is NOT a decision — it is a deferral.

DO NOT extract:
- CONDITIONAL statements. Any action governed by an "if" clause is NOT a commitment or decision, no matter how concrete the action sounds. "If we sign contracts, we'll move to Europe" contains no commitment — the "if" disqualifies it entirely.
- Status updates or context. "We have three months left", "we have a strong lead in Germany" — facts about the situation, not promises or resolutions.
- Hypothetical chains. "That funding may be in another jurisdiction, and if it comes from Europe they'd prefer us there" — speculation, not extractable.
- Persuasion or encouragement. "If you come here you will benefit" — an attempt to convince, not a commitment by anyone.
- Deferrals. "We'll consider it", "we'll see", "we'll know in three months" — these explicitly postpone commitment and decision; extract nothing from them.
- Travel or attendance intent. "I'm going to Jakarta" is a plan to be somewhere, not a commitment to deliver something. Only extract it if it is tied to a concrete deliverable someone is promised.

RULES:
- excerpt must be copied VERBATIM from the transcript — exactly as written, findable by exact string search in the cited turn. Do not clean up filler words or grammar.
- location must be the turn ID exactly as it appears, e.g. T-0043. Cite the turn that contains the excerpt.
- action must be self-contained: a reader who has never seen the transcript must understand it. Write "Alex to send Prathik the Jakarta itinerary", never "send it" or "send the document".
- raw_mention must be the speaker's name exactly as it appears in the transcript.
- If a single statement spans multiple turns (because another speaker interrupted), create ONE evidence entry PER turn. Each entry's excerpt must be verbatim from its own turn only. Never stitch words from different turns into one excerpt.
- The excerpt contains only the spoken words. Never include the speaker-name prefix or the turn ID in the excerpt.
- Transcripts contain transcription errors and run-on sentences. If an utterance appears garbled, extract only what is clearly asserted; put unclear fragments in the excerpt but do NOT incorporate uncertain words into the action. Lower confidence when the source is damaged.
- If transcription damage makes part of a commitment unrecoverable, write the action with an explicit gap marker: 'Alex to send Prathik his full [unclear — likely a document or schedule]'. Never substitute a specific guessed word
- A KEY FACT is a true, situationally important statement that is neither a promise nor a resolution: travel plans, dates, deadlines mentioned as context, the status of deals or relationships. "I'll be in Jakarta on the 17th of August" is a key fact. Key facts go in the key_facts list — never in commitments.

UNCERTAINTY POLICY: If a statement might be a commitment or decision but you are not sure it qualifies, INCLUDE it with confidence below 0.5 — never silently omit a possible commitment. This does not apply to the DO NOT EXTRACT categories above: those are definite exclusions. Apply the exclusion rules first; only statements that pass them are candidates for low-confidence inclusion.

EXAMPLE INPUT:
[T-0001 @00:05:12] Sam Lee: if the budget clears we'd probably expand the pilot
[T-0002 @00:05:30] Jo Park: I'll send you the revised scope document by Thursday
[T-0003 @00:05:45] Sam Lee: and heads up, the compliance audit starts March 3rd

CORRECT OUTPUT:
{{"commitments": [{{"action": "Jo Park to send Sam Lee the revised scope document",
  "owner": {{"kind": "unresolved", "raw_mention": "Jo Park"}},
  "due_text": "by Thursday",
  "evidence": [{{"location": "T-0002",
                "excerpt": "I'll send you the revised scope document by Thursday"}}],
    "key_facts": [{{"statement": "The compliance audit starts March 3rd",
  "evidence": [{{"location": "T-0003", "excerpt": "the compliance audit starts March 3rd"}}],
  "confidence": 0.9}}]
  

EXAMPLE INPUT 2 (statement interrupted across turns):
[T-0010 @00:12:01] Jo Park: I'll review the safety
[T-0011 @00:12:03] Sam Lee: Mhm.
[T-0012 @00:12:05] Jo Park: report before Friday's meeting
CORRECT OUTPUT:
{{"commitments": [{{"action": "Jo Park to review the safety report before Friday's meeting",
  "owner": {{"kind": "unresolved", "raw_mention": "Jo Park"}},
  "due_text": "before Friday's meeting",
  "evidence": [{{"location": "T-0010", "excerpt": "I'll review the safety"}},
               {{"location": "T-0012", "excerpt": "report before Friday's meeting"}}],
  "confidence": 0.9}}],
 "decisions": []}}
 



Now extract from this transcript:

<transcript>
{transcript}
</transcript>"""


def extract(transcript: str) -> ExtractionResult:
    schema = ExtractionResult.model_json_schema()
    raw = complete(
        "extraction",
        EXTRACTION_PROMPT.format(transcript=transcript),
        "confidential",
        schema=schema,
    )
    return ExtractionResult.model_validate_json(raw)




def _cut_window(lines: list[str], turn_id: str) -> str | None:
    idx = next((i for i, ln in enumerate(lines)
                if ln.startswith(f"[{turn_id} ")), None)
    if idx is None:
        return None
    lo, hi = max(0, idx - WINDOW), min(len(lines), idx + WINDOW + 1)
    return "\n".join(lines[lo:hi])


def _dedupe(items, key):
    seen, out = set(), []
    for it in items:
        k = key(it)
        if k not in seen:
            seen.add(k)
            out.append(it)
    return out


# ---------- PASS 1: scanner ----------

SCAN_PROMPT_VERSION = "v1"
SCAN_PROMPT = """You are scanning a meeting transcript to find turns worth closer analysis.

Flag a turn as "commitment" if a speaker promises or accepts a specific action ("I'll send you...", "I can do X").
Flag a turn as "decision" if the speakers settle a choice in this meeting ("let's go with X").
Flag a turn as "key_fact" if it states an important situational fact: travel plans, dates, deadlines, deal or relationship status.

Do NOT flag actions governed by an "if" clause — conditional plans are not commitments or decisions.
When unsure whether a turn qualifies, INCLUDE it — a later step will filter. Missing a real candidate is worse than a false one.

Return only turn IDs (exactly as written, e.g. T-0014) and the kind.

<transcript>
{transcript}
</transcript>"""


def _scan(transcript: str) -> ScanResult:
    raw = complete(
        "extraction_scan",
        SCAN_PROMPT.format(transcript=transcript),
        "confidential",
        schema=ScanResult.model_json_schema(),
        prompt_version=SCAN_PROMPT_VERSION,
    )
    return ScanResult.model_validate_json(raw)


# ---------- PASS 2: focused window extraction ----------

WINDOW_PROMPT_VERSION = "v1"
WINDOW_PROMPT = """You are given a SMALL WINDOW of a longer meeting transcript. Identify COMMITMENTS, DECISIONS, and KEY FACTS whose evidence is inside this window, and return JSON matching the schema.

A COMMITMENT is a promise or accepted request to perform a specific action: a speaker takes ownership ("I'll..."), of a concrete deliverable, directed at someone.
A DECISION is a resolution the speakers actually reached — a choice made, not deferred.
A KEY FACT is a true, situationally important statement that is neither: travel plans, dates, deadlines mentioned as context, deal or relationship status.

DO NOT extract actions governed by an "if" clause, hypotheticals, persuasion, deferrals ("we'll see"), or travel intent as commitments — travel plans belong in key_facts.

RULES:
- excerpt: copied VERBATIM from the transcript, findable by exact string search in the cited turn. Spoken words only — no speaker-name prefix, no turn ID.
- location: the turn ID exactly as written, e.g. T-0014.
- action/statement: self-contained — readable by someone who never saw the transcript.
- If transcription damage makes part of an item unrecoverable, use a gap marker like [unclear — likely a document or schedule]. Never substitute a guessed word. Lower confidence when the source is damaged.

An EMPTY result is correct and common. If nothing in this window qualifies, return empty lists. Do not force an extraction from a window that contains none.

<transcript_window>
{window}
</transcript_window>"""


def _extract_window(window: str) -> ExtractionResult:
    raw = complete(
        "extraction",
        WINDOW_PROMPT.format(window=window),
        "confidential",
        schema=ExtractionResult.model_json_schema(),
        prompt_version=WINDOW_PROMPT_VERSION,
    )
    return ExtractionResult.model_validate_json(raw)

def extract_two_pass(transcript: str) -> ExtractionResult:
    lines = transcript.splitlines()

    # 1. SCAN
    scan = _scan(transcript)

    # 2. For each candidate: cut window, run focused extraction
    all_c, all_d, all_k = [], [], []
    for cand in scan.candidate_turns:
        window = _cut_window(lines, cand.turn_id)
        if window is None:          # scanner returned a bogus turn ID
            continue                # TODO: log this — silent skip is temporary
        partial = _extract_window(window)
        all_c += partial.commitments
        all_d += partial.decisions
        all_k += partial.key_facts

    # 3. Merge + crude dedupe
    return ExtractionResult(
        commitments=_dedupe(all_c, key=lambda c: c.action.lower().strip()),
        decisions=_dedupe(all_d, key=lambda d: d.statement.lower().strip()),
        key_facts=_dedupe(all_k, key=lambda k: k.statement.lower().strip()),
    )

