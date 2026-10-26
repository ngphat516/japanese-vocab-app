from pydantic import BaseModel, ConfigDict, Field


class WordPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hanviet: str = Field(max_length=500)


class KanjiPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    hanviet: list[str] = Field(max_length=20)
