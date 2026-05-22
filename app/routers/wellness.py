from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone
from typing import List

from app.database import get_db
from app.models.user import User
from app.models.wellness import MoodLog
from app.schemas.wellness import MoodLogCreate, MoodLogResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/wellness", tags=["wellness"])


def calc_mood_score(mood: str, stress: int, energy: int | None, sleep: float | None) -> int:
    mood_base = {"happy": 90, "excited": 85, "calm": 80, "neutral": 60, "tired": 45, "anxious": 35, "sad": 30, "stressed": 25}
    base = mood_base.get(mood, 50)
    stress_penalty = (stress / 100) * 20
    energy_bonus = ((energy or 50) / 100) * 10
    sleep_bonus = min((sleep or 6) / 8, 1) * 10
    return max(0, min(100, int(base - stress_penalty + energy_bonus + sleep_bonus)))


@router.post("/mood", response_model=MoodLogResponse, status_code=201)
async def log_mood(
    data: MoodLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mood_score = data.mood_score or calc_mood_score(data.mood, data.stress_level, data.energy_level, data.sleep_hours)
    log = MoodLog(
        user_id=current_user.id,
        mood=data.mood,
        emoji=data.emoji,
        stress_level=data.stress_level,
        energy_level=data.energy_level,
        sleep_hours=data.sleep_hours,
        mood_score=mood_score,
        journal_note=data.journal_note,
        tags=data.tags,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log


@router.get("/mood", response_model=List[MoodLogResponse])
async def get_mood_history(
    days: int = Query(default=7, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(MoodLog)
        .where(MoodLog.user_id == current_user.id, MoodLog.logged_at >= since)
        .order_by(MoodLog.logged_at.desc())
    )
    return result.scalars().all()


@router.get("/mood/today", response_model=MoodLogResponse | None)
async def get_today_mood(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    today = datetime.now(timezone.utc).date()
    result = await db.execute(
        select(MoodLog)
        .where(
            MoodLog.user_id == current_user.id,
            func.date(MoodLog.logged_at) == today,
        )
        .order_by(MoodLog.logged_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


@router.get("/mood/stats")
async def get_mood_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(MoodLog).where(MoodLog.user_id == current_user.id, MoodLog.logged_at >= since)
    )
    logs = result.scalars().all()
    if not logs:
        return {"avg_mood_score": 0, "avg_stress": 0, "avg_sleep": 0, "avg_energy": 0, "count": 0}

    count = len(logs)
    return {
        "avg_mood_score": round(sum(l.mood_score or 0 for l in logs) / count, 1),
        "avg_stress": round(sum(l.stress_level for l in logs) / count, 1),
        "avg_sleep": round(sum(l.sleep_hours or 0 for l in logs) / count, 1),
        "avg_energy": round(sum(l.energy_level or 0 for l in logs) / count, 1),
        "count": count,
    }


@router.get("/mood/chart")
async def get_mood_chart(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(MoodLog)
        .where(MoodLog.user_id == current_user.id, MoodLog.logged_at >= since)
        .order_by(MoodLog.logged_at.asc())
    )
    logs = result.scalars().all()
    return [
        {
            "date": l.logged_at.strftime("%a"),
            "mood_score": l.mood_score,
            "stress": l.stress_level,
            "energy": l.energy_level,
            "sleep": l.sleep_hours,
        }
        for l in logs
    ]
