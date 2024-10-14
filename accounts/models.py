# from sqlalchemy import Column, String, Integer
# from sqlalchemy.orm import declarative_base
# from sqlalchemy.orm import relationship
# Base = declarative_base()

# class User(Base):
#     __tablename__ = 'users'
    
#     id = Column(Integer, primary_key=True, index=True)
#     email = Column(String, unique=True, index=True)
#     password = Column(String)
#     first_name = Column(String)
#     last_name = Column(String)
#     address = Column(String)
#     phone_number = Column(String)
#     education = Column(String)

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    address = Column(String)
    phone_number = Column(String)
    education = Column(String)
