"""The visual block of a mentor answer: a chart, a step diagram or a table, validated."""

import json
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StringConstraints,
    TypeAdapter,
    ValidationError,
    model_validator,
)

NonBlank = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class _VisualBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caption: NonBlank  # one line, shown under the visual
    alt_text: NonBlank  # text alternative for screen readers


class ChartVisual(_VisualBase):
    kind: Literal["chart"]
    chart_type: Literal["bar", "line", "pie"]
    labels: list[NonBlank] = Field(min_length=1, max_length=6)
    values: list[FiniteFloat] = Field(min_length=1, max_length=6)
    unit: str | None = None

    @model_validator(mode="after")
    def _check(self) -> ChartVisual:
        if len(self.labels) != len(self.values):
            raise ValueError("labels and values must have the same length")
        if self.chart_type == "pie" and any(v < 0 for v in self.values):
            raise ValueError("pie values must not be negative")
        return self


class StepsVisual(_VisualBase):
    kind: Literal["steps"]
    steps: list[NonBlank] = Field(min_length=2, max_length=5)


class TableVisual(_VisualBase):
    kind: Literal["table"]
    columns: list[NonBlank] = Field(min_length=1, max_length=3)
    rows: list[list[str]] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def _check(self) -> TableVisual:
        if any(len(row) != len(self.columns) for row in self.rows):
            raise ValueError("every row must have one cell per column")
        return self


type Visual = Annotated[
    ChartVisual | StepsVisual | TableVisual, Field(discriminator="kind")
]
VISUAL_ADAPTER: TypeAdapter[Visual] = TypeAdapter(Visual)
VISUAL_SCHEMA = json.dumps(VISUAL_ADAPTER.json_schema())


class VisualError(ValueError): ...


def parse_visual(raw: dict[str, Any] | None) -> dict[str, Any] | None:
    """None stays None; a valid visual comes back normalised; anything else raises."""
    if raw is None:
        return None
    try:
        return VISUAL_ADAPTER.validate_python(raw).model_dump()
    except ValidationError as e:
        raise VisualError(str(e)) from e
