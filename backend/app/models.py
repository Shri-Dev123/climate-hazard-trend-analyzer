from pydantic import BaseModel, Field, field_validator, model_validator


class BoundingBox(BaseModel):
    north: float = Field(..., ge=-90, le=90)
    south: float = Field(..., ge=-90, le=90)
    east: float = Field(..., ge=-180, le=180)
    west: float = Field(..., ge=-180, le=180)

    @model_validator(mode="after")
    def validate_bounds(self) -> "BoundingBox":
        if self.south >= self.north:
            raise ValueError("south must be less than north")
        if self.west >= self.east:
            raise ValueError("west must be less than east")
        return self


class Region(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    country: str | None = None
    admin1: str | None = None
    bbox: BoundingBox | None = None


class HeatwaveAnalysisRequest(BaseModel):
    region: Region
    start_year: int = Field(..., ge=1940, le=2100)
    end_year: int = Field(..., ge=1940, le=2100)
    hazard_type: str = "heatwave"

    @field_validator("hazard_type")
    @classmethod
    def validate_hazard(cls, value: str) -> str:
        if value.lower() != "heatwave":
            raise ValueError("only heatwave is supported in this implementation")
        return "heatwave"

    @model_validator(mode="after")
    def validate_years(self) -> "HeatwaveAnalysisRequest":
        if self.start_year > self.end_year:
            raise ValueError("start_year must be less than or equal to end_year")
        if self.end_year - self.start_year > 45:
            raise ValueError("time range cannot exceed 45 years")
        return self


class RegionSearchResult(BaseModel):
    id: int
    name: str
    country: str | None = None
    admin1: str | None = None
    latitude: float
    longitude: float


class HeatwaveEvent(BaseModel):
    start_date: str
    end_date: str
    duration_days: int
    max_temperature_c: float
    average_excess_c: float


class AnnualMetric(BaseModel):
    year: int
    event_count: int
    heatwave_days: int
    longest_event_days: int
    average_intensity_c: float
    rolling_heatwave_days: float | None = None


class TrendSummary(BaseModel):
    baseline_year: int
    latest_year: int
    baseline_heatwave_days: int
    latest_heatwave_days: int
    percent_change: float | None
    slope_days_per_year: float
    insight: str


class HeatwaveAnalysisResponse(BaseModel):
    analysis_id: str
    region: Region
    start_year: int
    end_year: int
    hazard_type: str
    threshold_c: float
    event_count: int
    heatwave_days: int
    annual: list[AnnualMetric]
    events: list[HeatwaveEvent]
    summary: TrendSummary
    source: str
    cached: bool

