from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)  # "   " fails min_length

    question: str = Field(min_length=1, max_length=500)


class SourceRef(BaseModel):
    page: int = Field(ge=1)
    snippet: str | None = None


class AskResponse(BaseModel):
    answer: str
    found: bool = Field(description="False when the document does not contain the answer")
    sources: list[SourceRef] = Field(default_factory=list)
