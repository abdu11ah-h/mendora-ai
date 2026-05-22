from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID
from datetime import datetime, timezone

from app.database import get_db
from app.models.user import User
from app.models.wellness import ChatSession, ChatMessage
from app.models.admin import RiskFlag
from app.schemas.wellness import ChatSessionResponse, ChatSessionCreate, SendMessageRequest
from app.dependencies import get_current_user
from app.services.gemini_service import get_gemini_response

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions", response_model=List[ChatSessionResponse])
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
    )
    sessions = result.scalars().all()
    # Return without messages for list view
    return [
        ChatSessionResponse(
            id=s.id, user_id=s.user_id, title=s.title,
            is_active=s.is_active, crisis_flag=s.crisis_flag,
            created_at=s.created_at, updated_at=s.updated_at, messages=[],
        )
        for s in sessions
    ]


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    data: ChatSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    session = ChatSession(user_id=current_user.id, title=data.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return ChatSessionResponse(
        id=session.id, user_id=session.user_id, title=session.title,
        is_active=session.is_active, crisis_flag=session.crisis_flag,
        created_at=session.created_at, updated_at=session.updated_at, messages=[],
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")
    await db.delete(session)
    await db.commit()


@router.post("/sessions/{session_id}/message")
async def send_message(
    session_id: UUID,
    data: SendMessageRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Load session
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    # Build Gemini history from existing messages
    history = []
    for msg in session.messages:
        role = "user" if msg.role == "user" else "model"
        history.append({"role": role, "parts": [msg.content]})

    # Save user message
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=data.content,
    )
    db.add(user_msg)

    # Auto-title session from first message
    if not session.title and not session.messages:
        session.title = data.content[:60] + ("..." if len(data.content) > 60 else "")

    # Get AI response
    ai_result = await get_gemini_response(data.content, history)

    # Save AI message
    ai_msg = ChatMessage(
        session_id=session.id,
        role="ai",
        content=ai_result["text"],
        crisis_detected=ai_result["crisis"],
        gemini_used=ai_result["gemini_used"],
    )
    db.add(ai_msg)

    # Flag session if crisis
    if ai_result["crisis"]:
        session.crisis_flag = True
        # Create risk flag
        flag = RiskFlag(
            student_id=current_user.id,
            triggered_by="crisis_keywords",
            severity="critical",
            message=f"Crisis keywords detected in chat. User message: {data.content[:200]}",
        )
        db.add(flag)

    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(ai_msg)

    return {"user_message": data.content, "ai_response": ai_result["text"], "crisis": ai_result["crisis"]}


@router.get("/sessions/{session_id}/export")
async def export_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ChatSession)
        .options(selectinload(ChatSession.messages))
        .where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(404, "Session not found")

    lines = [f"Mendora AI Chat Export", f"Session: {session.title or 'Untitled'}", f"Date: {session.created_at.strftime('%Y-%m-%d %H:%M')}", "---"]
    for msg in session.messages:
        prefix = "You" if msg.role == "user" else "Mendora"
        lines.append(f"[{msg.created_at.strftime('%H:%M')}] {prefix}: {msg.content}")

    return {"export": "\n".join(lines)}
