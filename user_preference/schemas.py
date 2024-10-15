from pydantic import BaseModel
from typing import List, Optional

# Topic schemas
class TopicCreate(BaseModel):
    name: str

class TopicResponse(BaseModel):
    id: int
    name: str

    class Config:
        orm_mode = True

# User Preference schemas
class UserPreferenceCreate(BaseModel):
    difficulty_level: str
    quiz_format: str
    topics: List[int]

class UserPreferenceResponse(BaseModel):
    id: int
    user_id: int
    difficulty_level: str
    quiz_format: str
    topics: List[TopicResponse]

    class Config:
        orm_mode = True
