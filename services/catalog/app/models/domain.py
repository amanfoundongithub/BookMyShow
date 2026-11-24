from datetime import datetime
from pydantic import BaseModel, Field


class ShowDoc(BaseModel):
    id: str = Field(alias="_id")
    movie_id: str
    cinema_id: str
    hall_id: str
    start_time: datetime
    end_time: datetime
    language: str
    format: str
    pricing: dict[str, float]