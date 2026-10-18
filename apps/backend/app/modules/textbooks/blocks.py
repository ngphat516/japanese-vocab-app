from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, TypeAdapter, model_validator


class BlockBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Meaning(BlockBase):
    type: Literal["meaning"]
    vi: str | None = None
    en: str | None = None

    @model_validator(mode="after")
    def has_meaning(self):
        if not self.vi and not self.en:
            raise ValueError("meaning requires vi or en")
        return self


class Example(BlockBase):
    type: Literal["example"]
    ja: str = Field(min_length=1)
    vi: str | None = None


class Variant(BlockBase):
    ja: str = Field(min_length=1)
    correct: bool = Field(strict=True)


class Usage(BlockBase):
    type: Literal["usage"]
    context: str | None = None
    variants: list[Variant] = Field(min_length=1)
    vi: str | None = None


class Collocation(BlockBase):
    type: Literal["collocation"]
    items: list[str] = Field(min_length=1)
    vi: str | None = None


class RelatedItem(BlockBase):
    text: str = Field(min_length=1)
    word_id: int | None = Field(default=None, gt=0)


class Relation(BlockBase):
    type: Literal["synonym", "antonym", "related"]
    items: list[RelatedItem] = Field(min_length=1)


class Note(BlockBase):
    type: Literal["note"]
    text: str = Field(min_length=1)


class Raw(BlockBase):
    type: Literal["raw"]
    data: JsonValue


Block = Annotated[
    Meaning | Example | Usage | Collocation | Relation | Note | Raw, Field(discriminator="type")
]
Content = Annotated[list[Block], Field(min_length=1)]
content_adapter = TypeAdapter(Content)


def validate_content(value):
    return [block.model_dump(exclude_none=True) for block in content_adapter.validate_python(value)]
