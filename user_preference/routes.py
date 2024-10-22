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
from langchain_community.tools import TavilySearchResults

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


@router.post("/preferences", response_model=schemas.UserPreferenceResponse)
def create_or_update_user_preference(
    preference: schemas.UserPreferenceCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    # Check if the user already has a preference
    existing_preference = db.query(models.UserPreference).filter_by(user_id=current_user.id).first()

    # Ensure topics exist
    topics = db.query(models.Topic).filter(models.Topic.id.in_(preference.topics)).all()
    if len(topics) != len(preference.topics):
        raise HTTPException(status_code=400, detail="One or more topics not found")

    if existing_preference:
        # Update existing preference
        existing_preference.difficulty_level = preference.difficulty_level
        existing_preference.quiz_format = preference.quiz_format
    else:
        # Create new preference entry
        existing_preference = models.UserPreference(
            user_id=current_user.id,
            difficulty_level=preference.difficulty_level,
            quiz_format=preference.quiz_format
        )
        db.add(existing_preference)

    # Commit changes to preferences
    db.commit()
    db.refresh(existing_preference)

    # Clear existing user topics and add new ones
    db.query(models.UserTopic).filter_by(user_id=current_user.id).delete()
    for topic_id in preference.topics:
        user_topic = models.UserTopic(user_id=current_user.id, topic_id=topic_id)
        db.add(user_topic)

    db.commit()

    # Fetch assigned topics to return in response
    existing_preference.topics = topics

    return existing_preference

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
    temperature=0.8,
    max_tokens=None,
    timeout=None,
    max_retries=3,
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

@router.get("/quiz-by-topic/")
def get_quiz_by_topic(topic_name: str, db: Session = Depends(get_db)):
    # Fetch the topic by name
    topic = db.query(models.Topic).filter(models.Topic.name == topic_name).first()
    
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # Fetch questions for the topic
    questions = db.query(models.Question).filter(models.Question.topic_id == topic.id).all()
    
    # Prepare the response in the expected format
    quiz_data = [
        {
            "question": question.question,
            "options": json.loads(question.options),  # Convert options back to a list
            "correct": question.correct,
            "topic": topic.name
        }
        for question in questions
    ]

    return {"quiz": quiz_data}


@router.post("/generate-quiz/")
def generate_quiz(db: Session = Depends(get_db),
             current_user: models.User = Depends(get_current_user)
             ):
    user_id = current_user.id
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

    # Extract quiz questions from the Pydantic model
    quiz_data = quiz_output.root  # Access the root attribute

    for item in quiz_data:
        topic_name = item.topic  # Access topic directly
        topic = db.query(models.Topic).filter_by(name=topic_name).first()
        if not topic:
            topic = models.Topic(name=topic_name)
            db.add(topic)
            db.commit()
            db.refresh(topic)

        question = models.Question(
            topic_id=topic.id,
            question=item.question,  # Access question text directly
            options=json.dumps(item.options),  # Store options as JSON string
            correct=item.correct  # Access correct answer directly
        )
        db.add(question)

    db.commit()

    

    return {"quiz": quiz_output}

@router.put("/track_performance", response_model=schemas.UserPerformanceResponse)
def track_user_performance(
    input_data: list[schemas.UserPerformanceCreate],  # Assuming input schema
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    user_id = current_user.id  # Extracted from bearer token

    total_questions = len(input_data)
    correct_count = 0
    incorrect_count = 0

    for data in input_data:
        topic_name = data.topic
        is_correct = data.is_correct

        # Find the topic in the database
        topic = db.query(models.Topic).filter(models.Topic.name == topic_name).first()
        if not topic:
            raise HTTPException(status_code=404, detail=f"Topic {topic_name} not found")

        # Find the user's performance for this topic
        performance = db.query(models.UserPerformance).filter(
            models.UserPerformance.user_id == user_id,
            models.UserPerformance.topic_id == topic.id
        ).first()

        # If no performance entry exists, create one
        if not performance:
            performance = models.UserPerformance(
                user_id=user_id,
                topic_id=topic.id,
                correct_count=0,
                incorrect_count=0
            )
            db.add(performance)
            db.commit()
            db.refresh(performance)

        # Update performance based on is_correct value
        if is_correct == 'true':
            performance.correct_count += 1
            correct_count += 1  # Count correct for this session
        else:
            performance.incorrect_count += 1
            incorrect_count += 1  # Count incorrect for this session

        db.commit()

    # Calculate the performance percentage for this session
    percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0

    # Return the detailed performance response
    return {
        "total_questions": total_questions,
        "correct_count": correct_count,
        "incorrect_count": incorrect_count,
        "percentage": percentage
    }

def generate_tavily_prompt(topic_name: str) -> str:
    """
    Generates a Tavily search prompt based on the topic name.
    """
    return f"Find top learning resources for {topic_name}. The resources should include tutorials, articles, videos, and courses that help improve understanding and skills in {topic_name}. Focus on beginner to intermediate level materials, emphasizing practical examples and hands-on learning."

@router.get("/recommend_resources")
def recommend_resources_for_user(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    user_id = current_user.id

    # Fetch the user's performance on all topics
    user_performances = db.query(models.UserPerformance).filter(
        models.UserPerformance.user_id == user_id
    ).all()

    if not user_performances:
        raise HTTPException(status_code=404, detail="No performance data found for the user")

    total_correct = 0
    total_incorrect = 0
    weak_topics = []

    # Calculate overall performance and identify weak topics
    for performance in user_performances:
        total_correct += performance.correct_count
        total_incorrect += performance.incorrect_count
        total_attempts = performance.correct_count + performance.incorrect_count

        if total_attempts > 0:
            topic_accuracy = (performance.correct_count / total_attempts) * 100
            if topic_accuracy < 90:  # Weak topic if accuracy is below 90%
                weak_topics.append(performance.topic_id)

    # Overall accuracy
    total_attempts = total_correct + total_incorrect
    overall_accuracy = (total_correct / total_attempts) * 100 if total_attempts > 0 else 0

    # If the overall performance is below 90%, recommend resources
    if overall_accuracy < 90:
        resources = []

        for topic_id in weak_topics:
            topic = db.query(models.Topic).filter(models.Topic.id == topic_id).first()

            if topic:
                # Generate Tavily search prompt for the topic
                search_prompt = generate_tavily_prompt(topic.name)

                # Use Tavily API to search for resources related to the topic
                tool = TavilySearchResults(
                    max_results=5,
                    search_depth="advanced",
                    include_answer=True,
                    include_raw_content=True,
                    include_images=True,
                )

                response_tavily = tool.invoke({"query": search_prompt})
                resources.append(
                    {
                        "topic": topic.name,
                        "resources": response_tavily
                    }
                )

        return {"overall_accuracy": overall_accuracy, "resources": resources}

    return {"overall_accuracy": overall_accuracy, "resources": []}

@router.get("/user_performance", response_model=schemas.UserOverallPerformanceResponse)
def get_user_performance(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    user_id = current_user.id  # Extracted from bearer token

    # Query the UserPerformance table to get the user's performance on all topics
    user_performance = db.query(models.UserPerformance).filter(models.UserPerformance.user_id == user_id).all()

    if not user_performance:
        raise HTTPException(status_code=404, detail="No performance data found for the user")

    # Create a list to hold performance results for each topic
    overall_performance = []

    # Loop through each topic performance and calculate the percentage
    for performance in user_performance:
        topic = db.query(models.Topic).filter(models.Topic.id == performance.topic_id).first()
        if topic:
            total_attempts = performance.correct_count + performance.incorrect_count
            percentage = (performance.correct_count / total_attempts * 100) if total_attempts > 0 else 0
            
            overall_performance.append({
                "topic": topic.name,
                "correct_count": performance.correct_count,
                "incorrect_count": performance.incorrect_count,
                "percentage": percentage
            })

    # Return the overall performance
    return {"user_id": user_id, "overall_performance": overall_performance}

@router.get("/gettopics")
def get_all_topics(db: Session = Depends(get_db)):
    topics = db.query(models.Topic).all()
    return topics

@router.get("/profile", response_model=schemas.UserProfileResponse)
def get_user_profile(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(get_current_user)
):
    user_id = current_user.id  # Extracted from bearer token

    # Fetch user information
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Fetch user topics
    user_topics = db.query(models.UserTopic).filter(models.UserTopic.user_id == user_id).all()
    topics = [db.query(models.Topic).filter(models.Topic.id == ut.topic_id).first() for ut in user_topics]

    # Prepare the response
    selected_topics = [schemas.UserTopicResponse(id=topic.id, name=topic.name) for topic in topics if topic]

    return schemas.UserProfileResponse(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        address=user.address,
        phone_number=user.phone_number,
        education=user.education,
        selected_topics=selected_topics
    )

