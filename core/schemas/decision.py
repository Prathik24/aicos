from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
from .evidence import SourceEvidence
from pydantic import model_validator
from .owners import Owner
from pydantic import ConfigDict
from .commitment import FounderVerdict


class Decision(BaseModel):
    """ Represents a decision made regarding a commitment. """
    schema_version: Literal["v1"] = "v1"
    decision_id: Optional[str] = None
    statement: str = Field(min_length=1)  # the decision statement
    rationale: Optional[str] = None  # optional rationale for the decision
    evidence: list[SourceEvidence] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    status: Literal["proposed", "approved", "edited", "rejected", "deferred"] = "proposed"
    verdict: Optional[FounderVerdict] = None
    owner: Owner  
    model_config = ConfigDict(extra="forbid")
    

    @model_validator(mode="after")
    def _status_verdict_consistent(self):
        if self.status != "proposed" and self.verdict is None:
            raise ValueError("non-proposed status requires a verdict")
        if self.status == "proposed" and self.decision_id is not None:
            raise ValueError("candidates must not carry a register ID")
        return self