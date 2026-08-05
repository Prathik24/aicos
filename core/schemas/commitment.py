from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
from .evidence import SourceEvidence
from pydantic import model_validator
from .owners import Owner

class FounderVerdict(BaseModel):
    """ FR-09"""
    verdict : Literal["approved" , "edited" , "rejected" , "defferred"]
    reason : Optional[str] = None
    decided_at : datetime

class Commitment(BaseModel):
    """ One promise/request. FR-03,04,05,06,07,08,09"""
    schema_version : Literal["v1"] = "v1"
    commitment_id : Optional[str] = None
    action : str = Field(min_length = 1) # what was promised, normalized
    owner : Owner  # who made the promise/request, normalized
    evidence: list[SourceEvidence] = Field(min_length=1)
    due_date : Optional[date] = None 
    due_text: Optional[str] = None 
    confidence : float = Field(ge = 0.0 , le = 1.0)
    status : Literal["proposed" , "approved" , "edited" , "rejected" , "defferred" , "fulfilled"] = "proposed"
    verdict : Optional[FounderVerdict] = None

    @model_validator(mode="after")
    def _status_verdict_consistent(self):
        if self.status != "proposed" and self.verdict is None:
            raise ValueError("non-proposed status requires a verdict")
        if self.status == "proposed" and self.commitment_id is not None:
            raise ValueError("candidates must not carry a register ID")
        return self


