from typing import Literal
from pydantic import BaseModel, Field


class ResolvedOwner(BaseModel):
    kind: Literal["resolved"] = "resolved"
    entity_id: str = Field(pattern=r"^PERSON-\d{4}$")

class UnresolvedOwner(BaseModel):
    kind: Literal["unresolved"] = "unresolved"
    raw_mention: str = Field(min_length=1)

Owner = ResolvedOwner | UnresolvedOwner   # a "discriminated union"