from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from accounts import models, schemas, auth
from accounts.models import User
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import timedelta
from database import SessionLocal
from sqlalchemy.exc import IntegrityError



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

# Signup API
@router.post("/signup", response_model=schemas.UserResponse)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    try:
        hashed_password = auth.get_password_hash(user.password)
        db_user = User(email=user.email, password=hashed_password, first_name=user.first_name, last_name=user.last_name, address=user.address, phone_number=user.phone_number, education=user.education)
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    except IntegrityError:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )

# Login API
@router.post("/login", response_model=schemas.Token)
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

    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user

@router.get("/dashboard", response_model=schemas.UserResponse)
def read_users_me(current_user: schemas.UserResponse = Depends(get_current_user)):
    return current_user

@router.post("/forgot", response_model=schemas.Message)
def forgot_password(form_data: schemas.UserForgot, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == form_data.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if form_data.new_password != form_data.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    
    user.password = auth.get_password_hash(form_data.new_password)
    db.commit()

    return {"message": "Password updated successfully"}
