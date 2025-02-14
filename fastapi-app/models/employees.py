from pydantic import BaseModel, Field
from datetime import datetime


class HiredEmployeeInsert(BaseModel):
    id: int = Field(..., example=1)
    name: str = Field(..., example="John Doe")
    hire_datetime: datetime = Field(..., example="2021-05-15T14:30:00Z")
    department_id: int = Field(..., example=2)
    job_id: int = Field(..., example=3)
