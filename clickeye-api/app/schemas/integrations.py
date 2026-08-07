from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator


class LinearValidateRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="Linear API 키 (lin_api_...)")
    team_id: str = Field(..., min_length=1, description="Linear 팀 UUID")


class NotionValidateRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="Notion 통합 API 키 (secret_...)")
    database_id: str = Field(..., min_length=1, description="Notion 데이터베이스 UUID")


class IntegrationValidateResponse(BaseModel):
    valid: bool
    message: str


class RegisterInitialTasksRequest(BaseModel):
    linear_api_key: str | None = Field(None, description="Linear API 키")
    linear_team_id: str | None = Field(None, description="Linear 팀 UUID")
    notion_api_key: str | None = Field(None, description="Notion API 키")
    notion_database_id: str | None = Field(None, description="Notion 데이터베이스 UUID")
    project_name: str = Field(..., min_length=1, description="프로젝트 이름")
    save_credentials: bool = Field(True, description="프로젝트별 자격증명 저장 여부")


class RegisterInitialTasksResponse(BaseModel):
    linear_created: bool
    linear_issue_url: str | None
    notion_created: bool
    notion_page_url: str | None
    errors: list[str]


class ProjectLinearStatusResponse(BaseModel):
    credentials_saved: bool
    team_id: str | None
    api_key_masked: str | None


class ProjectLinearCredentialsSave(BaseModel):
    api_key: str = Field(..., min_length=1, description="Linear API 키 (lin_api_...)")
    team_id: str = Field(..., min_length=1, description="Linear 팀 UUID")
    webhook_secret: str | None = Field(
        None, description="이 프로젝트 워크스페이스의 webhook signing secret"
    )
    tunnel_url: str | None = Field(
        None, description="webhook 수신 공개 URL (https). 미지정 시 사용자 전역 tunnel_url 폴백"
    )

    @field_validator("tunnel_url")
    @classmethod
    def _validate_tunnel_url(cls, value: str | None) -> str | None:
        """저장된 값이 그대로 Linear 훅의 전송 대상이 되므로 형식을 좁힌다.

        임의 문자열을 허용하면 워크스페이스 접근권자가 훅을 아무 URL 로나 재지향할 수
        있다. 호스트를 가진 https URL 만 받고, 빈 문자열은 미지정과 동일하게 취급한다.
        """
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("tunnel_url 은 호스트를 포함한 https URL 이어야 합니다")
        return value


class ProjectLinearCredentialsResponse(BaseModel):
    api_key_masked: str
    team_id: str
    webhook_secret_set: bool
    linear_webhook_id: str | None
    updated_at: datetime
