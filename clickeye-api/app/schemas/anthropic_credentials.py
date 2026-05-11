from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class AnthropicCredentialsSave(BaseModel):
    api_key: str = Field(..., min_length=10, description="Anthropic API 키")
    credential_type: Literal["api_key"] = Field(
        default="api_key",
        description="자격증명 유형 (api_key 고정)",
    )


class AnthropicCredentialsResponse(BaseModel):
    api_key_masked: str
    credential_type: str = "api_key"
    updated_at: datetime

    model_config = {"from_attributes": True}
