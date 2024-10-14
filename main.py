from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import SessionLocal, engine
from accounts import models, schemas, auth
from accounts.models import User
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from accounts.schemas import TokenData
from datetime import timedelta
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import IntegrityError

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # You can add specific origins or use ["*"] to allow all
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)

models.Base.metadata.create_all(bind=engine)
# OAuth2 scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
# Dependency for database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Signup API
@app.post("/signup", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        hashed_password = auth.get_password_hash(user.password)
        db_user = User(email=user.email, password=hashed_password,first_name=user.first_name,last_name=user.last_name,address=user.address,phone_number =user.phone_number,education=user.education)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        # Handle the UNIQUE constraint failure specifically
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )


# Login API
@app.post("/login", response_model=schemas.Token)
def login_for_access_token(form_data: schemas.UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data.email).first()
    if not user or not auth.verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Define token expiration (optional)
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Pass expires_delta as an argument
    access_token = auth.create_access_token(data={"sub": user.email}, expires_delta=access_token_expires)
    
    return {"access_token": access_token, "token_type": "bearer"}


# Function to get the current user by validating JWT
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        token_data = schemas.TokenData(email=email)
    except JWTError:
        raise credentials_exception

    # Fetch the user from the database
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user


@app.get("/dashboard", response_model=schemas.UserResponse)
def read_users_me(current_user: schemas.UserResponse = Depends(get_current_user)):
    return current_user


@app.post("/forgot", response_model=schemas.Message)  # Updated to return a message
def forgot_password(form_data: schemas.UserForgot, db: Session = Depends(get_db)):
    # Fetch the user by email
    user = db.query(models.User).filter(models.User.email == form_data.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if the new password and confirm password match
    if form_data.new_password != form_data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    # Hash the new password and update it in the database
    user.password = auth.get_password_hash(form_data.new_password)
    db.commit()

    return {"message": "Password updated successfully"}

# features

# @app.post("/user-preferences/", response_model=schemas.UserPreference)
# def create_user_preference(
#     preference: schemas.UserPreferenceCreate,
#     db: Session = Depends(get_db),
#     user: User = Depends(get_current_user)  # Assume you have a dependency for getting the current user
# ):
#     db_preference = models.UserPreference(**preference.dict(), user_id=user.id)  # Create the model instance
#     db.add(db_preference)
#     db.commit()
#     db.refresh(db_preference)
#     return db_preference

# @app.get("/user-preferences/{user_id}", response_model=schemas.UserPreference)
# def get_user_preference(user_id: int, db: Session = Depends(get_db)):
#     preference = db.query(models.UserPreference).filter(models.UserPreference.user_id == user_id).first()
#     if preference is None:
#         raise HTTPException(status_code=404, detail="User Preference not found")
#     return preference