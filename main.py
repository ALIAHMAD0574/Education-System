# main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from accounts.routes import router as accounts_router
from user_preference.routes import router as preferences_router
from database import SessionLocal, engine
# import accounts.models as models
from accounts.models import Base as AccountsBase
from user_preference.models import Base as PreferencesBase

app = FastAPI()


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Adjust as necessary
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Create the tables for both apps
AccountsBase.metadata.create_all(bind=engine)
PreferencesBase.metadata.create_all(bind=engine)

# Include the routers
app.include_router(accounts_router,prefix="/accounts", tags=["accounts"])
app.include_router(preferences_router, prefix="/users", tags=["preferences"])