from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.wellness import MoodLog, ChatSession
from app.models.admin import RiskFlag
from app.schemas.auth import UserProfile
from app.dependencies import require_role

router = APIRouter(prefix="/admin", tags=["admin"])

admin_only = require_role("admin")


@router.get("/users")
async def list_users(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    role: str | None = None,
    is_active: bool | None = None,
    admin=Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    q = select(User)
    if role:
        q = q.where(User.role == role)
    if is_active is not None:
        q = q.where(User.is_active == is_active)
    q = q.offset((page - 1) * size).limit(size)
    result = await db.execute(q)
    users = result.scalars().all()
    return {"users": [UserProfile.model_validate(u) for u in users], "page": page, "size": size}


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: UUID,
    admin=Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    mood_result = await db.execute(select(func.count()).where(MoodLog.user_id == user_id))
    chat_result = await db.execute(select(func.count()).where(ChatSession.user_id == user_id))

    return {
        "user": UserProfile.model_validate(user),
        "mood_log_count": mood_result.scalar(),
        "chat_session_count": chat_result.scalar(),
    }


@router.put("/users/{user_id}")
async def update_user(
    user_id: UUID,
    is_active: bool | None = None,
    role: str | None = None,
    admin=Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    if is_active is not None:
        user.is_active = is_active
    if role:
        user.role = role
    await db.commit()
    return {"message": "User updated"}


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: UUID,
    admin=Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    await db.delete(user)
    await db.commit()


@router.get("/stats")
async def platform_stats(admin=Depends(admin_only), db: AsyncSession = Depends(get_db)):
    total_users = (await db.execute(select(func.count(User.id)))).scalar()
    total_chats = (await db.execute(select(func.count(ChatSession.id)))).scalar()
    risk_count = (await db.execute(select(func.count(RiskFlag.id)).where(RiskFlag.resolved == False))).scalar()
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    active_sessions = (
        await db.execute(
            select(func.count(User.id)).where(
                User.last_login.isnot(None),
                User.last_login >= since_24h,
            )
        )
    ).scalar()
    student_count = (
        await db.execute(select(func.count(User.id)).where(User.role == "student"))
    ).scalar()
    return {
        "total_users": total_users,
        "total_chat_sessions": total_chats,
        "unresolved_risk_flags": risk_count,
        "active_sessions": active_sessions,
        "student_count": student_count,
    }


@router.get("/risk-flags")
async def list_risk_flags(admin=Depends(admin_only), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RiskFlag).where(RiskFlag.resolved == False).order_by(RiskFlag.created_at.desc())
    )
    flags = result.scalars().all()
    return [
        {
            "id": str(f.id), "student_id": str(f.student_id), "triggered_by": f.triggered_by,
            "severity": f.severity, "message": f.message, "created_at": f.created_at,
        }
        for f in flags
    ]


@router.put("/risk-flags/{flag_id}")
async def resolve_risk_flag(
    flag_id: UUID,
    admin=Depends(admin_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RiskFlag).where(RiskFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(404, "Flag not found")
    flag.resolved = True
    flag.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Flag resolved"}


@router.get("/wellness-overview")
async def wellness_overview(admin=Depends(admin_only), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(func.avg(MoodLog.mood_score), func.avg(MoodLog.stress_level), func.count(MoodLog.id))
    )
    row = result.one()
    return {
        "avg_mood_score": round(float(row[0] or 0), 1),
        "avg_stress": round(float(row[1] or 0), 1),
        "total_mood_logs": row[2],
    }
