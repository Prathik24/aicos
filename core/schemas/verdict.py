


from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, model_validator


class VerdictEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: Literal["approved", "edited", "rejected", "deferred"]
    edited_text: Optional[str] = None    # required when verdict == "edited"
    reason: Optional[str] = None         # required when verdict == "rejected"

    @model_validator(mode="after")
    def _consistent(self):
        # YOU: edited requires edited_text; rejected requires reason.
        if self.verdict == "edited" and self.edited_text is None:
            raise ValueError("edited requires edited_text")
        if self.verdict == "rejected" and self.reason is None:
            raise ValueError("rejected requires reason")
        return self

class VerdictFile(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decided_at: datetime
    entries: dict[str, VerdictEntry]     # natural key -> verdict   