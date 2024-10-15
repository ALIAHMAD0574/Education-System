from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from user_preference import models, schemas
from accounts import auth
from database import SessionLocal
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

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
