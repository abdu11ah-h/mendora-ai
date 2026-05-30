from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta, timezone

def _format_last_active(dt: datetime | None) -> str:
    if not dt:
        return "Never"
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    delta = now - dt
    if delta.days > 0:
        return f"{delta.days}d ago"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"
    mins = max(1, delta.seconds // 60)
    return f"{mins}m ago"


def _status_from_risk(risk_level: str) -> str:
    if risk_level in ("high", "critical"):
        return "At Risk"
    if risk_level == "medium":
        return "Monitoring"
    return "Stable"
from typing import List
from uuid import UUID

from app.database import get_db
from app.models.user import User
from app.models.wellness import MoodLog, ChatSession
from app.models.admin import CounselorNote, RiskFlag
from app.schemas.admin import CounselorNoteCreate, CounselorNoteUpdate, CounselorNoteResponse
from app.dependencies import require_role

router = APIRouter(prefix="/counselor", tags=["counselor"])

counselor_only = require_role("counselor", "admin")


@router.get("/students")
async def list_students(
    counselor=Depends(counselor_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.role == "student", User.is_active == True))
    students = result.scalars().all()

    out = []
    for s in students:
        flag_result = await db.execute(
            select(RiskFlag).where(RiskFlag.student_id == s.id, RiskFlag.resolved == False).order_by(RiskFlag.severity.desc()).limit(1)
        )
        top_flag = flag_result.scalar_one_or_none()
        risk_level = top_flag.severity if top_flag else "low"

        mood_result = await db.execute(
            select(MoodLog)
            .where(MoodLog.user_id == s.id)
            .order_by(MoodLog.logged_at.desc())
            .limit(1)
        )
        latest_mood = mood_result.scalar_one_or_none()

        session_count = (
            await db.execute(select(func.count()).select_from(ChatSession).where(ChatSession.user_id == s.id))
        ).scalar() or 0

        out.append({
            "id": str(s.id),
            "name": f"{s.first_name} {s.last_name}",
            "email": s.email,
            "university": s.university,
            "risk_level": risk_level,
            "risk": risk_level,
            "mood_score": latest_mood.mood_score if latest_mood and latest_mood.mood_score is not None else 0,
            "mood": latest_mood.mood_score if latest_mood and latest_mood.mood_score is not None else 0,
            "sessions": session_count,
            "last_active": _format_last_active(s.last_login),
            "lastSeen": _format_last_active(s.last_login),
            "status": _status_from_risk(risk_level),
        })
    return out


@router.get("/students/{student_id}")
async def get_student_detail(
    student_id: UUID,
    counselor=Depends(counselor_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == student_id, User.role == "student"))
    student = result.scalar_one_or_none()
    if not student:
        raise HTTPException(404, "Student not found")

    since = datetime.now(timezone.utc) - timedelta(days=30)
    moods = await db.execute(
        select(MoodLog).where(MoodLog.user_id == student_id, MoodLog.logged_at >= since).order_by(MoodLog.logged_at.desc())
    )
    mood_list = moods.scalars().all()

    flags = await db.execute(
        select(RiskFlag).where(RiskFlag.student_id == student_id, RiskFlag.resolved == False)
    )

    return {
        "student": {"id": str(student.id), "name": f"{student.first_name} {student.last_name}", "email": student.email},
        "mood_trend": [{"date": str(m.logged_at.date()), "score": m.mood_score, "stress": m.stress_level} for m in mood_list],
        "risk_flags": [{"id": str(f.id), "severity": f.severity, "message": f.message} for f in flags.scalars().all()],
    }


@router.post("/notes", response_model=CounselorNoteResponse, status_code=201)
async def add_note(
    data: CounselorNoteCreate,
    counselor=Depends(counselor_only),
    db: AsyncSession = Depends(get_db),
):
    note = CounselorNote(
        counselor_id=counselor.id,
        student_id=data.student_id,
        note=data.note,
        is_private=data.is_private,
        risk_level=data.risk_level,
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.get("/notes/{student_id}", response_model=List[CounselorNoteResponse])
async def get_notes(
    student_id: UUID,
    counselor=Depends(counselor_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CounselorNote)
        .where(CounselorNote.student_id == student_id, CounselorNote.counselor_id == counselor.id)
        .order_by(CounselorNote.created_at.desc())
    )
    return result.scalars().all()


@router.put("/notes/{note_id}", response_model=CounselorNoteResponse)
async def update_note(
    note_id: UUID,
    data: CounselorNoteUpdate,
    counselor=Depends(counselor_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CounselorNote).where(CounselorNote.id == note_id, CounselorNote.counselor_id == counselor.id)
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(404, "Note not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


@router.get("/alerts")
async def get_alerts(counselor=Depends(counselor_only), db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RiskFlag)
        .where(RiskFlag.resolved == False, RiskFlag.severity.in_(["high", "critical"]))
        .order_by(RiskFlag.created_at.desc())
    )
    flags = result.scalars().all()
    out = []
    for f in flags:
        student_result = await db.execute(select(User).where(User.id == f.student_id))
        student = student_result.scalar_one_or_none()
        name = f"{student.first_name} {student.last_name}" if student else "Unknown"
        out.append({
            "id": str(f.id),
            "student_id": str(f.student_id),
            "name": name,
            "severity": f.severity,
            "risk": f.severity,
            "message": f.message,
            "created_at": f.created_at,
            "lastSeen": _format_last_active(f.created_at),
        })
    return out


@router.post("/alerts/{flag_id}/acknowledge")
async def acknowledge_alert(
    flag_id: UUID,
    counselor=Depends(counselor_only),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RiskFlag).where(RiskFlag.id == flag_id))
    flag = result.scalar_one_or_none()
    if not flag:
        raise HTTPException(404, "Alert not found")
    flag.resolved = True
    flag.resolved_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Alert acknowledged"}
