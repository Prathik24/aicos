# pipeline/ingest.py
import re

TS_LINE = re.compile(r"^\d{2}:\d{2}:\d{2}\s*$")       # bare timestamp line
SPEAKER_LINE = re.compile(r"^([A-Z][\w .'-]+?): (.*)$")  # 'Name: text' — captures both
BACKCHANNEL = re.compile(
    r"^(mhm|yeah|okay|ok|sure|see|right|yes|uh-huh|mm)[.!? ]*$", re.I
)
# KNOWN LIMIT: a genuine one-word answer ("Okay." accepting a proposal) is
# indistinguishable from backchannel and will be merged away. Accepted for MVP.
# KNOWN LIMIT: speaker names must start with a capital Latin letter.


def _parse_turns(raw: str) -> list[dict]:
    """Phase 1: raw text -> [{'speaker','text','ts'}], no numbering."""
    turns = []
    current_ts = "unknown"
    for line in raw.splitlines():
        line = line.rstrip()
        if not line:
            continue
        if TS_LINE.match(line):
            current_ts = line.strip()
            continue
        m = SPEAKER_LINE.match(line)
        if m:
            turns.append({"speaker": m.group(1), "text": m.group(2), "ts": current_ts})
        elif turns:
            turns[-1]["text"] += " " + line   # continuation
    return turns


def _merge_backchannels(turns: list[dict]) -> list[dict]:
    """Phase 2: drop pure-backchannel turns that split a same-speaker sentence."""
    merged = list(turns)
    changed = True
    while changed:                # loop: Mhm/Yeah chains stack
        changed = False
        i = 0
        while i + 2 < len(merged):
            a, b, c = merged[i], merged[i + 1], merged[i + 2]
            if (a["speaker"] == c["speaker"]
                    and a["speaker"] != b["speaker"]
                    and BACKCHANNEL.match(b["text"].strip())):
                a["text"] += " " + c["text"]
                del merged[i + 1: i + 3]      # drop backchannel + folded turn
                changed = True
            else:
                i += 1
    return merged


def number_turns(raw: str) -> str:
    """'[T-0001 @hh:mm:ss] Speaker: text' per turn, backchannel splits repaired."""
    turns = _merge_backchannels(_parse_turns(raw))
    return "\n".join(
        f"[T-{i:04d} @{t['ts']}] {t['speaker']}: {t['text']}"
        for i, t in enumerate(turns, start=1)
    )