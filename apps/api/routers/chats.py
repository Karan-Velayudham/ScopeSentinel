import asyncio
import re
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from sqlmodel import select, desc, func
from sqlalchemy.orm import selectinload
import structlog

from db.session import TenantSessionDep
from auth.rbac import CurrentUserDep
from db.models import ChatSession, ChatMessage, GeneratedFile, MessageRole, MessageType, Agent
from schemas import (
    ChatSessionCreateRequest, ChatSessionResponse, ChatSessionListResponse,
    ChatMessageCreateRequest, ChatMessageResponse, ChatMessageListResponse,
    GeneratedFileResponse, PaginationMeta
)
from agent_utils import (
    build_system_prompt,
    get_tools_for_agent,
    execute_platform_tool,
    build_remote_tools_for_chat,
    execute_remote_tool,
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

    # Persist user message
    user_msg = ChatMessage(
        org_id=org_id, chat_session_id=chat_id, role=MessageRole.USER,
        content=request.content, message_type=MessageType.TEXT
    )
    session.add(user_msg)
    await session.commit()

    # Load agent with skills eagerly (Phase 1: skill injection)
    result = await session.execute(
        select(Agent)
        .where(Agent.id == chat.agent_id)
        .options(selectinload(Agent.skills))
    )
    agent = result.scalars().first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent mapping invalid")

    def _resolve_model(model: str) -> str:
        """Ensure model name has a LiteLLM provider prefix."""
        if not model or "/" in model:
            return model
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
        return model

    # --- Phase 1: Build system prompt with skill instructions ---
    skills = list(agent.skills) if agent.skills else []
    system_prompt = build_system_prompt(agent, skills)

    # --- Phase 2: Load tools ---
    # 2a. Remote MCP tools from adapter-service (Jira, GitHub, etc.)
    mcp_tool_defs, mcp_tool_registry = await build_remote_tools_for_chat(org_id)
    # 2b. Platform capability tools (web search, memory) as additional tools
    platform_tools = get_tools_for_agent(agent)
    # Merge: MCP tools take priority; platform tools fill in the rest
    all_tools = mcp_tool_defs + [
        t for t in platform_tools
        if t["function"]["name"] not in {d["function"]["name"] for d in mcp_tool_defs}
    ]

    # Fetch full conversation history
    stmt = select(ChatMessage).where(ChatMessage.chat_session_id == chat_id).order_by(ChatMessage.created_at)
    history_result = await session.execute(stmt)
    history = history_result.scalars().all()

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for msg in history:
        role_str = msg.role.value if hasattr(msg.role, "value") else msg.role
        role_type = "assistant" if role_str == "agent" else "user"
        messages.append({"role": role_type, "content": msg.content})

    # Safety: ensure current input is in the messages list
    if not any(m.get("content") == request.content and m.get("role") == "user" for m in messages):
        messages.append({"role": "user", "content": request.content})

    resolved_model = _resolve_model(agent.model)
    logger.info("chat_llm_call", model=agent.model, resolved=resolved_model,
                chat_id=chat_id, skills=len(skills),
                remote_tools=len(mcp_tool_defs), platform_tools=len(platform_tools))

    # --- Phase 3: Synchronous ReAct loop (max 5 iterations) ---
    from litellm import acompletion

    MAX_ITERATIONS = 5
    agent_text = ""

    try:
        for iteration in range(MAX_ITERATIONS):
            call_kwargs: dict = {
                "model": resolved_model,
                "messages": messages,
                "timeout": agent.timeout_seconds,
            }
            if all_tools:
                call_kwargs["tools"] = all_tools
                call_kwargs["tool_choice"] = "auto"

            response = await acompletion(**call_kwargs)
            choice = response.choices[0]
            finish_reason = choice.finish_reason
            resp_message = choice.message

            # If the LLM returned a direct text response, we're done
            if finish_reason == "stop" or not getattr(resp_message, "tool_calls", None):
                agent_text = resp_message.content or ""
                break

            # --- Tool call(s) detected: execute and feed results back ---
            # Append the assistant's tool-calling turn to messages
            messages.append(resp_message.model_dump(exclude_unset=True))

            tool_calls = resp_message.tool_calls
            for tc in tool_calls:
                tool_name = tc.function.name
                tool_args = tc.function.arguments
                logger.info("chat_tool_call", tool=tool_name, chat_id=chat_id, iteration=iteration)

                tool_result = await execute_remote_tool(
                    tool_name, tool_args, mcp_tool_registry, org_id
                )

                logger.info("chat_tool_result", tool=tool_name, chat_id=chat_id,
                            result_len=len(str(tool_result)))

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": str(tool_result),
                })
        else:
            # Max iterations reached without a text response
            agent_text = "I've taken several actions but couldn't form a complete answer within the allowed steps. Please try asking again with more specifics."

    except Exception as e:
        logger.error("chat_llm_failed", error=str(e), chat_id=chat_id)
        agent_text = f"An error occurred during response generation: {e}"

    # Persist the final assistant message
    agent_msg = ChatMessage(
        org_id=org_id, chat_session_id=chat_id, role=MessageRole.AGENT,
        content=agent_text, message_type=MessageType.STRUCTURED
    )
    session.add(agent_msg)
    await session.commit()
    await session.refresh(agent_msg)

    # Parse and persist any file artifacts embedded in the response
    files_created = []
    file_pattern = re.compile(r'<file name="(.*?)">(.*?)</file>', re.DOTALL)
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
