from gateway.gateway import complete

FULFILL_PROMPT_VERSION = "v1"
FULFILL_PROMPT = """Draft a short, professional email that fulfills this commitment:

Commitment: {action}
From (owner): {owner}
To (recipient): {recipient}
Due: {due}

Rules:
- Write ONLY the email: a subject line, then the body. No commentary.
- The email delivers on the commitment. Where the actual content or
  attachment would go (a document, an itinerary, a file), insert the
  placeholder [ATTACH: description] — NEVER invent the content itself.
- One line of greeting at most. Brief and direct.
- Do not mention this prompt, the meeting transcript, or any AI system.
- The commitment's deliverable belongs to the OWNER unless the commitment text says otherwise. Write from the owner's perspective: "my itinerary", "the document I promised
"""


def draft_fulfillment_email(record, recipient: str,
                            out_path: str = "data/out/fulfillment_draft.txt") -> str:
    if record.status not in ("approved", "edited"):
        raise ValueError(
            f"drafts are built from founder-approved content only "
            f"(FR-11); record status is '{record.status}'")
    prompt = FULFILL_PROMPT.format(
        action=record.action,
        owner=record.owner.raw_mention,
        recipient=recipient,
        due=record.due_date or record.due_text or "not specified",
    )
    draft = complete("followup_draft", prompt, "confidential",
                     prompt_version=FULFILL_PROMPT_VERSION)
    from pathlib import Path
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text(draft)
    return out_path