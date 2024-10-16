from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from user_preference import models, schemas
from accounts import auth
from database import SessionLocal
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain_groq import ChatGroq
import getpass
import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
import json
from pydantic import BaseModel,RootModel
from langchain.output_parsers import PydanticOutputParser

# "mcqs","true/false"

# Load environment variables from .env file
load_dotenv('.env')

router = APIRouter()

# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get current user from JWT
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(models.User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

# Create user preference
@router.post("/preferences", response_model=schemas.UserPreferenceResponse)
def create_user_preference(preference: schemas.UserPreferenceCreate, 
                           db: Session = Depends(get_db), 
                           current_user: models.User = Depends(get_current_user)):
    # Check if the user already has a preference
    existing_preference = db.query(models.UserPreference).filter_by(user_id=current_user.id).first()
    if existing_preference:
        raise HTTPException(status_code=400, detail="User preferences already exist. Please update your preferences.")                       


    # Ensure topics exist
    topics = db.query(models.Topic).filter(models.Topic.id.in_(preference.topics)).all()
    if len(topics) != len(preference.topics):
        raise HTTPException(status_code=400, detail="One or more topics not found")

    # Create preference entry
    user_pref = models.UserPreference(
        user_id=current_user.id,
        difficulty_level=preference.difficulty_level,
        quiz_format=preference.quiz_format
    )
    db.add(user_pref)
    db.commit()
    db.refresh(user_pref)

    # Assign topics to user
    for topic_id in preference.topics:
        user_topic = models.UserTopic(user_id=current_user.id, topic_id=topic_id)
        db.add(user_topic)
    db.commit()

    # Fetch assigned topics to return in response
    user_pref.topics = topics

    return user_pref

# Get user preferences
@router.get("/preferences", response_model=schemas.UserPreferenceResponse)
def get_user_preference(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    user_pref = db.query(models.UserPreference).filter(models.UserPreference.user_id == current_user.id).first()
    if not user_pref:
        raise HTTPException(status_code=404, detail="User preferences not found")

    topics = db.query(models.Topic).join(models.UserTopic).filter(models.UserTopic.user_id == current_user.id).all()
    user_pref.topics = topics

    return user_pref

# Create a new topic
@router.post("/topics", response_model=schemas.TopicResponse)
def create_topic(topic: schemas.TopicCreate, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Ensure the topic does not already exist
    existing_topic = db.query(models.Topic).filter(models.Topic.name == topic.name).first()
    if existing_topic:
        raise HTTPException(status_code=400, detail="Topic already exists")

    # Create the new topic
    new_topic = models.Topic(name=topic.name)
    db.add(new_topic)
    db.commit()
    db.refresh(new_topic)

    return new_topic

@router.put("/preferences", response_model=schemas.UserPreferenceResponse)
def update_user_preference(preference: schemas.UserPreferenceCreate, 
                           db: Session = Depends(get_db), 
                           current_user: models.User = Depends(get_current_user)):
    # Fetch existing preference
    user_pref = db.query(models.UserPreference).filter_by(user_id=current_user.id).first()
    if not user_pref:
        raise HTTPException(status_code=404, detail="User preferences not found")

    # Ensure topics exist
    topics = db.query(models.Topic).filter(models.Topic.id.in_(preference.topics)).all()
    if len(topics) != len(preference.topics):
        raise HTTPException(status_code=400, detail="One or more topics not found")

    # Update preference fields
    user_pref.difficulty_level = preference.difficulty_level
    user_pref.quiz_format = preference.quiz_format
    db.commit()

    # Update topics for the user
    # First, delete old topics
    db.query(models.UserTopic).filter_by(user_id=current_user.id).delete()
    db.commit()

    # Now, add new topics
    for topic_id in preference.topics:
        user_topic = models.UserTopic(user_id=current_user.id, topic_id=topic_id)
        db.add(user_topic)
    db.commit()

    # Fetch assigned topics to return in response
    user_pref.topics = topics

    return user_pref

class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct: str
    topic : str

class Quiz(RootModel):
    root: list[QuizQuestion]

# Set up the PydanticOutputParser to parse quiz data into the expected format
parser = PydanticOutputParser(pydantic_object=Quiz)

def create_quiz_prompt():
    prompt_template = PromptTemplate(
        input_variables=["number_of_questions", "topics", "difficulty_level", "quiz_format"],
        template="""

            Generate {number_of_questions} quiz questions based on the following user preferences:
            - Topics: {topics}
            - Difficulty Level: {difficulty_level}
            - Quiz Format: {quiz_format}

            If the quiz format is "MCQs", provide questions with four answer options, where one is the correct answer.

            If the quiz format is "True/False", provide questions with two options: "true" and "false".

            Return the output as a JSON array, where each object contains:
            - "question": The quiz question text.
            - "options": An array of answer options.
            - "correct": The correct answer.
            - "topic": The topic the question belongs to, which should be from the list of user-defined topics.

            Example response for MCQs:
            [
                {{
                    "question": "What is the correct machine learning type from the below options?",
                    "options": ["supervised learning", "AI learning", "computer learning", "science learning"],
                    "correct": "supervised learning",
                    "topic": "machine learning"
                }},
                {{
                    "question": "What does GPT stand for?",
                    "options": ["General Processing Tensor", "Generative Pretrained Transformer", "Graphics Processing Temperature", "Generative Pretrained Transformer"],
                    "correct": "Generative Pretrained Transformer",
                    "topic": "AI"
                }}
            ]

            Example response for True/False:
            [
                {{
                    "question": "Is regression a type of supervised machine learning?",
                    "options": ["true", "false"],
                    "correct": "true",
                    "topic": "machine learning"
                }},
                {{
                    "question": "Is classification a type of unsupervised machine learning?",
                    "options": ["true", "false"],
                    "correct": "false",
                    "topic": "AI"
                }}
            ]

            Generate questions based on the user input now.
            """
                            
        ,partial_variables={"format_instructions": parser.get_format_instructions()})
    
    return prompt_template  # Return the PromptTemplate object, not the formatted string


# Initialize LLM
def get_openai_llm():
    llm = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro",
    temperature=0.5,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    # other params...
)
    return llm

# Function to generate the quiz using LangChain
def generate_quiz_with_langchain(preferences, topics):
    # Initialize OpenAI LLM
    llm = get_openai_llm()

    # Create the LangChain LLM chain with a proper PromptTemplate object
    prompt_template = create_quiz_prompt()
    
    # Create the LLMChain to process the prompt and parse the response
    chain = prompt_template | llm | parser

    # Generate the prompt values dynamically
    prompt_values = {
        "number_of_questions": 5,
        "topics": ", ".join([t for t in topics]),  # Format topics into a string
        "difficulty_level": preferences.difficulty_level,
        "quiz_format": preferences.quiz_format
    }

    # Run the chain with the prompt values
    quiz_output = chain.invoke(prompt_values)

    return quiz_output

@router.post("/generate-quiz/")
def generate_quiz(user_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    # Fetch user preferences from the database
    preferences = db.query(models.UserPreference).filter(models.UserPreference.user_id == user_id).first()
    if not preferences:
        raise HTTPException(status_code=404, detail="User preferences not found")
    
    # Fetch topics selected by the user by joining UserTopic and Topic tables
    topics = db.query(models.Topic.name).join(models.UserTopic).filter(models.UserTopic.user_id == user_id).all()
    
    if not topics:
        raise HTTPException(status_code=404, detail="User topics not found")

    # Convert fetched topics from list of tuples to a list of strings
    topics = [topic[0] for topic in topics]
    

    # Generate quiz using OpenAI LLM through LangChain
    quiz_output = generate_quiz_with_langchain(preferences, topics)


    return {"quiz": quiz_output}

