from pydantic import BaseModel, Field
from typing import List


class InsertResponse(BaseModel):
    success: bool = Field(..., example=True)
    message: str = Field(...,
                         example="10 records inserted into hired_employees")
    failed_records: List[dict] = Field(..., example=[])
