from datetime import date, datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field
from pydantic import model_validator
from pydantic import ConfigDict


class GatewayCall(BaseModel):
    """ Represents a call made to an external gateway. """
    schema_version: Literal["v1"] = "v1"
    timestamp: datetime  # when the call was made
    task : str = Field(min_length=1)  # the task associated with the call
    data_class : str = Field(min_length=1)  # the data class associated with the call
    tier : str = Field(min_length=1)  # the tier associated with the call
    provider : str = Field(min_length=1)  # the provider associated with the call
    model : str = Field(min_length=1)  # the model associated with the call
    prompt_version : str = Field(min_length=1)  # the prompt version associated with the call
    outcome: Literal["success", "failure"]  # the outcome of the call
    error : Optional[str] = None  # the error message if the call failed
    payload_preview : Optional[str] = None  # a preview of the payload sent to the gateway
    model_config = ConfigDict(extra="forbid")
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    duration_ms: Optional[int] = None
    load_ms: Optional[int] = None
    eval_ms: Optional[int] = None
    done_reason: Optional[str] = None

    @model_validator(mode="after")
    def _outcome_error_consistent(self):
        if self.outcome == "failure" and self.error is None:
            raise ValueError("failure requires an error message")
        if self.outcome == "success" and self.error is not None:
            raise ValueError("success must not carry an error")
        return self


    