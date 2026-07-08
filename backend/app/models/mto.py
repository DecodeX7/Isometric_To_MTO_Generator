from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Category(str, Enum):
    PIPE = "PIPE"
    FITTING = "FITTING"
    FLANGE = "FLANGE"
    VALVE = "VALVE"
    GASKET = "GASKET"
    BOLT = "BOLT"
    SUPPORT = "SUPPORT"
    INSTRUMENT = "INSTRUMENT"
    WELD = "WELD"
    OTHER = "OTHER"


class DrawingMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    drawing_no: str = "Unknown"
    revision: str = "Unknown"
    line_number: str = "Unknown"
    nps: str = "Unknown"
    material_class: str = "Unknown"
    service: str = "Unknown"


class MTOItem(BaseModel):
    model_config = ConfigDict(use_enum_values=True, extra="ignore")

    item_no: int = Field(..., ge=1, description="Sequential MTO row number")
    category: Category
    description: str = Field(default="", description="Engineering item description")
    size_nps: str = Field(default="", description="Nominal Pipe Size, e.g. 6\" or 6\"x4\"")
    schedule_rating: str = Field(default="", description="Pipe schedule or pressure class")
    material_spec: str = Field(default="", description="ASTM/ASME material grade")
    end_type: str = Field(default="", description="BW, SW, THD, FLGD, etc.")
    quantity: float = Field(default=0, ge=0)
    unit: str = Field(default="EA", description="M, EA, NO, SET")
    length_m: float | None = Field(default=None, ge=0)
    confidence: float | None = Field(default=None, ge=0, le=1)
    remarks: str = ""

    @field_validator("category", mode="before")
    @classmethod
    def normalize_category(cls, value: Any) -> Any:
        if value is None:
            return Category.OTHER.value
        if isinstance(value, Category):
            return value.value
        normalized = str(value).strip().upper()
        aliases = {
            "PIPES": "PIPE",
            "FITTINGS": "FITTING",
            "FLANGES": "FLANGE",
            "VALVES": "VALVE",
            "GASKETS": "GASKET",
            "BOLTS": "BOLT",
            "BOLT SET": "BOLT",
            "BOLT SETS": "BOLT",
            "SUPPORTS": "SUPPORT",
            "WELDS": "WELD",
        }
        return aliases.get(normalized, normalized)

    @field_validator("unit", "end_type", mode="before")
    @classmethod
    def normalize_upper_text(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().upper()

    @model_validator(mode="after")
    def normalize_pipe_fields(self) -> "MTOItem":
        if self.category == Category.PIPE.value:
            self.unit = "M"
            if self.length_m is None and self.quantity > 0:
                # Some models return pipe length in quantity. Preserve it as length.
                self.length_m = float(self.quantity)
                self.quantity = 1
        return self


class Summary(BaseModel):
    model_config = ConfigDict(extra="ignore")

    total_pipe_length_m: float = 0
    fittings: int = 0
    flanges: int = 0
    valves: int = 0
    gaskets: int = 0
    bolt_sets: int = 0
    supports: int = 0
    field_welds: int = 0


class ExtractionInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    provider: str = "mock"
    model: str = "mock"
    mode: str = "mock"
    warnings: list[str] = Field(default_factory=list)


class MTOResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    drawing_meta: DrawingMeta = Field(default_factory=DrawingMeta)
    items: list[MTOItem] = Field(default_factory=list)
    summary: Summary = Field(default_factory=Summary)
    extraction_info: ExtractionInfo = Field(default_factory=ExtractionInfo)
