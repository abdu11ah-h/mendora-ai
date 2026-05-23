from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import os
from dotenv import load_dotenv

from app.database import get_db

load_dotenv()

from app.routers import auth, wellness, chat, focus, admin, counselor

app = FastAPI(
    title="Mendora AI Backend",
    description="University Mental Wellness Platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow local dev hosts + production FRONTEND_URL
_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_frontend = os.getenv("FRONTEND_URL", "").strip().rstrip("/")
if _frontend and _frontend not in _cors_origins:
    _cors_origins.append(_frontend)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_origin_regex=r"https://.*\.(up\.railway\.app|vercel\.app|netlify\.app)$",
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


@app.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok", "database": "connected"}
