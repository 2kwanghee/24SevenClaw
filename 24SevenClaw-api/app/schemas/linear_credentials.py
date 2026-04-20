from datetime import datetime

from pydantic import BaseModel, Field


class LinearCredentialsSave(BaseModel):
    api_key: str = Field(..., min_length=10, description="Linear API 키 (lin_api_...)")
    team_id: str = Field(..., min_length=1, description="Linear 팀 ID (UUID)")
    webhook_secret: str | None = Field(None, description="Webhook 서명 검증 시크릿")
    tunnel_url: str | None = Field(None, description="Cloudflare/ngrok 터널 URL")


class LinearCredentialsResponse(BaseModel):
    api_key_masked: str
    team_id: str
    webhook_secret_set: bool
    tunnel_url: str | None
    linear_webhook_id: str | None
    updated_at: datetime

    model_config = {"from_attributes": True}
