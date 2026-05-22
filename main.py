from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

from app.routers import auth, wellness, chat, focus, admin, counselor

app = FastAPI(
    title="Mendora AI Backend",
    description="University Mental Wellness Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        os.getenv("FRONTEND_URL", "http://localhost:3000"),
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
PREFIX = "/api/v1"
app.include_router(auth.router, prefix=PREFIX)
app.include_router(wellness.router, prefix=PREFIX)
app.include_router(chat.router, prefix=PREFIX)
app.include_router(focus.router, prefix=PREFIX)
app.include_router(admin.router, prefix=PREFIX)
app.include_router(counselor.router, prefix=PREFIX)


@app.get("/")
async def root():
    return {"message": "Mendora AI API is running", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}
