from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base
from accounts.models import User  # Import the User model from accounts

class UserPerformance(Base):
    __tablename__ = 'user_performance'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)  # Assuming you're tracking by user
    topic_id = Column(Integer, ForeignKey('topics.id'))
    correct_count = Column(Integer, default=0)
    incorrect_count = Column(Integer, default=0)
    
    topic = relationship("Topic", back_populates="performances")

class Topic(Base):
    __tablename__ = 'topics'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)

    performances = relationship("UserPerformance", back_populates="topic")
    
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

class Question(Base):
    __tablename__ = 'questions'
    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey('topics.id'))
    question = Column(String, nullable=False)
    options = Column(String, nullable=False)  # JSON stored as string
    correct = Column(String, nullable=False)

User.preferences = relationship("UserPreference", back_populates="user", uselist=False)
User.user_topics = relationship("UserTopic", back_populates="user", cascade="all, delete-orphan")
Topic.user_topics = relationship("UserTopic", back_populates="topic", cascade="all, delete-orphan")
