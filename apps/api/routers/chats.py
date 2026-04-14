import asyncio
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlmodel import select, desc, func
import structlog

from db.session import TenantSessionDep
from auth.rbac import CurrentUserDep
from db.models import ChatSession, ChatMessage, GeneratedFile, MessageRole, MessageType, Agent
from schemas import (
    ChatSessionCreateRequest, ChatSessionResponse, ChatSessionListResponse,
    ChatMessageCreateRequest, ChatMessageResponse, ChatMessageListResponse,
    GeneratedFileResponse, PaginationMeta
)

router = APIRouter(prefix="/api", tags=["Chats"])
logger = structlog.get_logger(__name__)


@router.post("/chats", response_model=ChatSessionResponse)
async def create_chat_session(
    request: ChatSessionCreateRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    req: Request,
):
    org_id = getattr(req.state, "org_id", None) or current_user.org_id
    chat = ChatSession(
        org_id=org_id,
        agent_id=request.agent_id,
        title=request.title or "New Chat Session"
    )
    session.add(chat)
    await session.commit()
    await session.refresh(chat)
    return ChatSessionResponse(
        id=chat.id,
        org_id=chat.org_id,
        agent_id=chat.agent_id,
        title=chat.title,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
    )


@router.get("/chats", response_model=ChatSessionListResponse)
async def list_chats(
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    req: Request,
    page: int = 1,
    page_size: int = 50
):
    org_id = getattr(req.state, "org_id", None) or current_user.org_id
    stmt = (
        select(ChatSession)
        .where(ChatSession.org_id == org_id)
        .order_by(desc(ChatSession.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await session.execute(stmt)
    items = result.scalars().all()
    
    count_stmt = select(func.count()).select_from(ChatSession).where(ChatSession.org_id == org_id)
    total_result = await session.execute(count_stmt)
    total = total_result.scalar() or 0
    
    return ChatSessionListResponse(
        items=[
            ChatSessionResponse(
                id=c.id,
                org_id=c.org_id,
                agent_id=c.agent_id,
                title=c.title,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
            for c in items
        ],
        meta=PaginationMeta(total=total, page=page, page_size=page_size, has_next=(len(items) == page_size))
    )


@router.get("/chats/{chat_id}/messages", response_model=ChatMessageListResponse)
async def list_messages(
    chat_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    req: Request,
):
    org_id = getattr(req.state, "org_id", None) or current_user.org_id
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.org_id == org_id, ChatMessage.chat_session_id == chat_id)
        .order_by(ChatMessage.created_at)
    )
    result = await session.execute(stmt)
    messages = result.scalars().all()
    
    files_stmt = select(GeneratedFile).where(GeneratedFile.chat_session_id == chat_id)
    files_result = await session.execute(files_stmt)
    all_files = files_result.scalars().all()
    
    msg_responses = []
    for m in messages:
        m_files = [f for f in all_files if f.message_id == m.id]
        msg_responses.append(ChatMessageResponse(
            id=m.id, org_id=m.org_id, chat_session_id=m.chat_session_id,
            role=m.role, content=m.content, message_type=m.message_type,
            created_at=m.created_at, files=m_files
        ))
        
    return ChatMessageListResponse(items=msg_responses, meta=None)


@router.post("/chats/{chat_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    chat_id: str,
    request: ChatMessageCreateRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    req: Request,
):
    org_id = getattr(req.state, "org_id", None) or current_user.org_id
    chat = await session.get(ChatSession, chat_id)
    if not chat or chat.org_id != org_id:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    user_msg = ChatMessage(
        org_id=org_id, chat_session_id=chat_id, role=MessageRole.USER,
        content=request.content, message_type=MessageType.TEXT
    )
    session.add(user_msg)
    await session.commit()
    
    agent = await session.get(Agent, chat.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent mapping invalid")
        
    from litellm import acompletion

    def _resolve_model(model: str) -> str:
        """Ensure model name has a LiteLLM provider prefix."""
        if not model or "/" in model:
            return model  # already prefixed or empty
        if model.startswith("claude"):
            if "claude-3" in model or "latest" in model:
                return "anthropic/claude-sonnet-4-6"
            return f"anthropic/{model}"
        if model.startswith("gpt") or model.startswith("o1") or model.startswith("o3"):
            return f"openai/{model}"
        if model.startswith("gemini"):
            return f"google/{model}"
        if model.startswith("mistral") or model.startswith("mixtral"):
            return f"mistral/{model}"
        return model  # unknown — pass through as-is

    # Fetch history
    stmt = select(ChatMessage).where(ChatMessage.chat_session_id == chat_id).order_by(ChatMessage.created_at)
    result = await session.execute(stmt)
    history = result.scalars().all()
    
    system_prompt = f"[System Instructions]\n{agent.instructions}"
    messages = [{"role": "system", "content": system_prompt}]
    
    for msg in history:
        role_str = msg.role.value if hasattr(msg.role, 'value') else msg.role
        role_type = "assistant" if role_str == "agent" else "user"
        messages.append({"role": role_type, "content": msg.content})
        
    # In case history wasn't committed fast enough, append current user input explicitly
    if not any(m["content"] == request.content for m in messages):
        messages.append({"role": "user", "content": request.content})

    resolved_model = _resolve_model(agent.model)
    logger.info("chat_llm_call", model=agent.model, resolved=resolved_model, chat_id=chat_id)

    try:
        response = await acompletion(
            model=resolved_model,
            messages=messages,
            timeout=agent.timeout_seconds,
        )
        agent_text = response.choices[0].message.content
    except Exception as e:
        logger.error("chat_llm_failed", error=str(e), chat_id=chat_id)
        agent_text = f"An error occurred during response generation: {e}"
        
    agent_msg = ChatMessage(
        org_id=org_id, chat_session_id=chat_id, role=MessageRole.AGENT,
        content=agent_text, message_type=MessageType.STRUCTURED
    )
    session.add(agent_msg)
    await session.commit()
    await session.refresh(agent_msg)
    
    files_created = []
    file_pattern = re.compile(r'<file name="(.*?)">(.*?)</file>', re.DOTALL)
    
    # Parse for files
    for match in file_pattern.finditer(agent_text):
        fname, fcontent = match.groups()
        gen_file = GeneratedFile(
            org_id=org_id, chat_session_id=chat_id, message_id=agent_msg.id,
            filename=fname, content=fcontent.strip()
        )
        session.add(gen_file)
        files_created.append(gen_file)
        
    if files_created:
        await session.commit()
        for f in files_created:
            await session.refresh(f)
            
    return ChatMessageResponse(
        id=agent_msg.id, org_id=agent_msg.org_id, chat_session_id=agent_msg.chat_session_id,
        role=agent_msg.role, content=agent_msg.content, message_type=agent_msg.message_type,
        created_at=agent_msg.created_at, files=files_created
    )


@router.get("/chats/{chat_id}/files", response_model=list[GeneratedFileResponse])
async def list_files(
    chat_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    req: Request,
):
    org_id = getattr(req.state, "org_id", None) or current_user.org_id
    stmt = select(GeneratedFile).where(GeneratedFile.org_id == org_id, GeneratedFile.chat_session_id == chat_id)
    result = await session.execute(stmt)
    files = result.scalars().all()
    return [
        GeneratedFileResponse(
            id=f.id, org_id=f.org_id, chat_session_id=f.chat_session_id,
            message_id=f.message_id, filename=f.filename, file_type=f.file_type,
            created_at=f.created_at
        )
        for f in files
    ]


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    req: Request,
):
    org_id = getattr(req.state, "org_id", None) or current_user.org_id
    file_record = await session.get(GeneratedFile, file_id)
    if not file_record or file_record.org_id != org_id:
        raise HTTPException(status_code=404, detail="File not found")
        
    return PlainTextResponse(
        content=file_record.content,
        headers={"Content-Disposition": f"attachment; filename=\"{file_record.filename}\""}
    )
