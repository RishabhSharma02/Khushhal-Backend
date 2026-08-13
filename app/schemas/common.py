
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(
        from_attributes=True,
        use_enum_values=True,
        protected_namespaces=(),
    )


class PageEnvelope(BaseModel, Generic[T]):
    items: list[T]
    next_cursor: str | None = None
