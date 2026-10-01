from pydantic import BaseModel, ConfigDict, Field


class Edit(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    path: str = Field(min_length=1, max_length=1024)
    content: str = Field(max_length=32_000)


class FixProposal(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    diagnosis: str = Field(min_length=1, max_length=8000)
    edits: list[Edit] = Field(max_length=40)
