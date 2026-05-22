from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.focus import FocusSession
from app.schemas.admin import FocusSessionCreate, FocusSessionUpdate, FocusSessionResponse
from app.dependencies import get_current_user

router = APIRouter(prefix="/focus", tags=["focus"])


@router.post("/sessions", response_model=FocusSessionResponse, status_code=201)
async def start_session(
    data: FocusSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = FocusSession(
        user_id=current_user.id,
        mode=data.mode,
        duration_mins=data.duration_mins,
        notes=data.notes,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.put("/sessions/{session_id}", response_model=FocusSessionResponse)
async def update_session(
    session_id: UUID,
    data: FocusSessionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FocusSession).where(FocusSession.id == session_id, FocusSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(session, field, value)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=List[FocusSessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FocusSession)
        .where(FocusSession.user_id == current_user.id)
        .order_by(FocusSession.started_at.desc())
    )
    return result.scalars().all()


@router.get("/stats")
async def focus_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    since = datetime.now(timezone.utc) - timedelta(days=7)
    result = await db.execute(
        select(FocusSession).where(FocusSession.user_id == current_user.id, FocusSession.started_at >= since)
    )
    sessions = result.scalars().all()
    total_mins = sum(s.actual_mins or 0 for s in sessions)
    completions = sum(1 for s in sessions if s.completed)
    total_distractions = sum(s.distractions for s in sessions)

    return {
        "total_hours": round(total_mins / 60, 2),
        "total_sessions": len(sessions),
        "completions": completions,
        "completion_rate": round(completions / len(sessions) * 100, 1) if sessions else 0,
        "total_distractions": total_distractions,
    }
