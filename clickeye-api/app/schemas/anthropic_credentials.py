from datetime import datetime

from pydantic import BaseModel, Field


class AnthropicCredentialsSave(BaseModel):
    api_key: str = Field(..., min_length=20, description="Anthropic API 키 (sk-ant-...)")


class AnthropicCredentialsResponse(BaseModel):
    api_key_masked: str
    updated_at: datetime

    model_config = {"from_attributes": True}
