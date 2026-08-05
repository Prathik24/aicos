from typing import Literal
from pydantic import BaseModel, Field

class SourceEvidence(BaseModel):
    """
    Represents the source of evidence for a given claim or statement.
    """
    source_id : str = Field(pattern = r"SRC-\d{4}$")
    source_type: Literal['email', 'transcript', 'document'] 
    location : str = Field(min_length = 1) # message-ID
    excerpt : str = Field(min_length = 1 , max_length = 1000)

        