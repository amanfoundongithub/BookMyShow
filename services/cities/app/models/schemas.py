from pydantic import BaseModel, Field


class CreateCityRequest(BaseModel):
    id: str | None = Field(default=None, min_length=2, max_length=80)
    name: str = Field(..., min_length=2, max_length=120)
    state: str = Field(..., min_length=2, max_length=120)
    country: str = Field(default="India", min_length=2, max_length=120)


class UpdateCityRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    state: str | None = Field(default=None, min_length=2, max_length=120)
    country: str | None = Field(default=None, min_length=2, max_length=120)


class CityResponse(BaseModel):
    id: str
    name: str
    state: str
    country: str
