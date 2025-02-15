from pydantic import BaseModel, Field


class DepartmentInsert(BaseModel):
    id: int = Field(..., example=1)
    department: str = Field(..., example="Engineering")
