from pydantic import BaseModel
from typing import Union

class UserCreate(BaseModel):
    email: str
    password: str
    first_name:str
    last_name:str
    address: str
    phone_number:str
    education:str

class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: str
    first_name:str
    last_name:str

    class Config:
        orm_mode = True

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Union[str, None]
