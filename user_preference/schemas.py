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


class UserPerformanceCreate(BaseModel):
    topic: str
    is_correct: str  # You might want to use a boolean here for easier processing

class UserPerformanceResponse(BaseModel):
    total_questions: int
    correct_count: int
    incorrect_count: int
    percentage: float

    class Config:
        orm_mode = True

class UserTopicPerformance(BaseModel):
    topic: str
    correct_count: int
    incorrect_count: int
    percentage: float

    class Config:
        orm_mode = True

class UserOverallPerformanceResponse(BaseModel):
    user_id: int
    overall_performance: List[UserTopicPerformance]

    class Config:
        orm_mode = True        

class UserTopicResponse(BaseModel):
    id: int
    name: str

class UserProfileResponse(BaseModel):
    first_name: str
    last_name: str
    email: str
    address: str
    phone_number: str
    education: str
    selected_topics: List[UserTopicResponse]

    class Config:
        orm_mode = True