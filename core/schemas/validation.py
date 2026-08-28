from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

from core.schemas.commitment import Commitment
from core.schemas.decision import Decision
from core.schemas.extraction import CandidateKeyFact
from .evidence import SourceEvidence
from pydantic import model_validator
from .owners import Owner
from pydantic import ConfigDict
from .owners import UnresolvedOwner


class Flag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    record_key: str          # natural key of the flagged record
    rule: Literal["date_in_action_without_due", "anchor_failed",
                  "due_unparseable", "duplicate_merged"]
    detail: str

class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")
    flags: list[Flag]
    commitments : list[Commitment] 
    decisions : list[Decision] 
    key_facts : list[CandidateKeyFact] 