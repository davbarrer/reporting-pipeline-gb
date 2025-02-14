from pydantic import BaseModel, Field
from typing import List


class InsertRequest(BaseModel):
    table: str = Field(..., example="hired_employees")
    data: List[dict]  # Raw data, validated dynamically
