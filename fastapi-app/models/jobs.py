from pydantic import BaseModel, Field


class JobInsert(BaseModel):
    id: int = Field(..., example=1)
    job: str = Field(..., example="Software Engineer")
