from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from accounts.models import User  # Adjust the import path as necessary

Base = declarative_base()

class Topic(Base):
    __tablename__ = 'topics'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class UserPreference(Base):
    __tablename__ = 'user_preferences'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))  # Reference to User model
    difficulty_level = Column(String)  # e.g., beginner, intermediate, advanced
    quiz_format = Column(String)  # e.g., multiple-choice, true/false, open-ended
    
    user = relationship("User", back_populates="preferences")  # Ensure User is imported correctly
    topics = relationship("Topic", secondary="user_topics")

# Create an association table for many-to-many relationship
class UserTopics(Base):
    __tablename__ = 'user_topics'
    
    user_id = Column(Integer, ForeignKey('users.id'), primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id'), primary_key=True)
