from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
from .evidence import SourceEvidence
from pydantic import model_validator
from .owners import Owner
from pydantic import ConfigDict
from .owners import UnresolvedOwner

class CandidateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location: str = Field(min_length=1)   # timestamp/message-id as seen in the text
    excerpt: str = Field(min_length=1, max_length=1000)

class CandidateCommitment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: str = Field(min_length=1)
    owner: UnresolvedOwner            # ONLY unresolved — no union, no ResolvedOwner import
    due_text: Optional[str] = None    # raw phrase only; no due_date field exists here
    evidence: list[SourceEvidence] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[CandidateEvidence] = Field(min_length=1)

class CandidateDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    statement: str = Field(min_length=1)
    owner: UnresolvedOwner            # ONLY unresolved — no union, no ResolvedOwner import
    rationale: Optional[str] = None
    evidence: list[SourceEvidence] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[CandidateEvidence] = Field(min_length=1)

class CandidateKeyFact(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # No owner field: a fact is about the world, not owed by anyone.
    # Deliberately no category enum for MVP — see TODO.md.
    statement: str = Field(min_length=1)
    evidence: list[CandidateEvidence] = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)

class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    commitments: list[CandidateCommitment]
    decisions: list[CandidateDecision]
    key_facts: list[CandidateKeyFact]

class CandidateTurn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_id: str = Field(min_length=1)          # e.g. "T-0014"
    kind: Literal["commitment", "decision", "key_fact"]
class ScanResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_turns: list[CandidateTurn]


    


