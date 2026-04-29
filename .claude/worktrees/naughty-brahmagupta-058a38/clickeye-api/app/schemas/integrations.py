from pydantic import BaseModel, Field


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
