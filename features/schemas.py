from pydantic import BaseModel

class UserPreferenceBase(BaseModel):
    difficulty_level: str  # e.g., beginner, intermediate, advanced
    quiz_format: str  # e.g., multiple-choice, true/false, open-ended

class UserPreferenceCreate(UserPreferenceBase):
    pass  # No additional fields needed for creation

class UserPreference(UserPreferenceBase):
    id: int  # Include the ID for the response

    class Config:
        orm_mode = True  # Enable ORM mode to read data from SQLAlchemy models
