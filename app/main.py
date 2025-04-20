from fastapi import FastAPI
from app.routes import router

# Create FastAPI app instance
app = FastAPI()

# Include API routes
app.include_router(router)

# The app and config setup is handled by the imported modules 