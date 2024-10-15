from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from accounts.models import User  # Import the User model from accounts

class Topic(Base):
    __tablename__ = 'topics'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

class UserPreference(Base):
    __tablename__ = 'user_preferences'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    difficulty_level = Column(String)
    quiz_format = Column(String)

    user = relationship("User", back_populates="preferences")

class UserTopic(Base):
    __tablename__ = 'user_topics'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    topic_id = Column(Integer, ForeignKey('topics.id'))

    user = relationship("User", back_populates="user_topics")
    topic = relationship("Topic", back_populates="user_topics")

User.preferences = relationship("UserPreference", back_populates="user", uselist=False)
User.user_topics = relationship("UserTopic", back_populates="user", cascade="all, delete-orphan")
Topic.user_topics = relationship("UserTopic", back_populates="topic", cascade="all, delete-orphan")
