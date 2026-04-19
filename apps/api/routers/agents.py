import json
from typing import Annotated, Optional
import structlog
from fastapi import APIRouter, HTTPException, Query, status, Request
from sqlmodel import select, func

from sqlalchemy.orm import selectinload
from auth.api_keys import CurrentUserDep
from db.models import Agent, Skill, AgentSkillLink, AgentStatus, OAuthConnection, AgentAppConnectionLink
from db.session import TenantSessionDep
from schemas import (
    PaginationMeta,
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentResponse,
    AgentListResponse,
    AgentExecuteRequest,
    AgentExecuteResponse,
    AgentRunResponse,
    AgentRunListResponse,
    AgentRunDetailResponse,
)
from db.models import AgentRun, AgentRunStatus, AgentRunTriggeredBy
from agent_utils import build_system_prompt

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])

def build_prompt(agent: Agent, skills: list[Skill], user_input: dict) -> str:
    """Wrapper around the shared build_system_prompt + user input section."""
    system = build_system_prompt(agent, skills)
    return system + f"\n\n[Input]\n{json.dumps(user_input)}"

def _agent_to_response(agent: Agent, skills: Optional[list[Skill]] = None, app_connections: Optional[list[OAuthConnection]] = None) -> AgentResponse:
    # Use provided skills or extract from agent if already loaded (selectinload)
    skill_ids = []
    if skills is not None:
        skill_ids = [s.id for s in skills]
    else:
        # Check if skills were eagerly loaded
        try:
            skill_ids = [s.id for s in agent.skills]
        except Exception:
            # Fallback to empty if not loaded to avoid lazy load error
            skill_ids = []

    app_conn_ids = []
    if app_connections is not None:
        app_conn_ids = [c.id for c in app_connections]
    else:
        try:
            app_conn_ids = [c.id for c in agent.app_connections]
        except Exception:
            app_conn_ids = []

    return AgentResponse(
        id=agent.id,
        org_id=agent.org_id,
        name=agent.name,
        description=agent.description,
        instructions=agent.instructions,
        model=agent.model,
        timeout_seconds=agent.timeout_seconds,
        app_connections=app_conn_ids,
        skills=skill_ids,
        capabilities=agent.capabilities,
        status=agent.status.value if hasattr(agent.status, "value") else agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )

@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreateRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> AgentResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    agent = Agent(
        org_id=org_id,
        name=body.name,
        description=body.description,
        instructions=body.instructions,
        model=body.model,
        timeout_seconds=body.timeout_seconds,
        status=body.status,
        capabilities=dict(body.capabilities) if body.capabilities else None,
    )
    
    if body.skills:
        # Resolve skills for the org
        skills = (await session.exec(select(Skill).where(Skill.org_id == org_id, Skill.id.in_(body.skills)))).all()
        agent.skills = list(skills)

    if body.app_connections:
        connections = (await session.exec(select(OAuthConnection).where(OAuthConnection.org_id == org_id, OAuthConnection.id.in_(body.app_connections)))).all()
        agent.app_connections = list(connections)

    session.add(agent)
    await session.commit()
    # Skip refresh to avoid potential 500 during session-persisted refresh
    
    logger.info("api.agent_created", agent_id=agent.id, org_id=org_id)
    return _agent_to_response(
        agent, 
        skills=agent.skills if body.skills else [],
        app_connections=agent.app_connections if body.app_connections else []
    )

@router.get("/", response_model=AgentListResponse)
async def list_agents(
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AgentListResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    query = select(Agent).where(Agent.org_id == org_id).options(selectinload(Agent.skills), selectinload(Agent.app_connections)).order_by(Agent.created_at.desc())
    
    count_query = select(func.count()).select_from(
        select(Agent.id).where(Agent.org_id == org_id).subquery()
    )
    total = (await session.exec(count_query)).one()
    
    offset = (page - 1) * page_size
    agents = (await session.exec(query.offset(offset).limit(page_size))).all()
    
    return AgentListResponse(
        items=[_agent_to_response(a) for a in agents],
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        ),
    )

@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> AgentResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    agent = (await session.exec(
        select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
        .options(selectinload(Agent.skills), selectinload(Agent.app_connections))
    )).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return _agent_to_response(agent)

@router.put("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    body: AgentUpdateRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> AgentResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    agent = (await session.exec(
        select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
        .options(selectinload(Agent.skills), selectinload(Agent.app_connections))
    )).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    has_changes = False
    
    if body.name is not None:
        agent.name = body.name
        has_changes = True
    if body.description is not None:
        agent.description = body.description
        has_changes = True
    if body.instructions is not None:
        agent.instructions = body.instructions
        has_changes = True
    if body.model is not None:
        agent.model = body.model
        has_changes = True
    if body.timeout_seconds is not None:
        agent.timeout_seconds = body.timeout_seconds
        has_changes = True
    if body.app_connections is not None:
        connections = (await session.exec(select(OAuthConnection).where(OAuthConnection.org_id == org_id, OAuthConnection.id.in_(body.app_connections)))).all()
        agent.app_connections = list(connections)
        has_changes = True
    if body.skills is not None:
        skills = (await session.exec(select(Skill).where(Skill.org_id == org_id, Skill.id.in_(body.skills)))).all()
        agent.skills = list(skills)
        has_changes = True
    if body.status is not None:
        agent.status = body.status
        has_changes = True
    if body.capabilities is not None:
        agent.capabilities = dict(body.capabilities)  # copy to ensure mutation is detected
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(agent, "capabilities")
        has_changes = True
        
    if has_changes:
        import datetime
        agent.updated_at = datetime.datetime.now(datetime.timezone.utc)
        session.add(agent)
        await session.commit()
        # Skip refresh to avoid potential 500
        logger.info("api.agent_updated", agent_id=agent.id, org_id=org_id)
        
    return _agent_to_response(agent)

@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> None:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    agent = (await session.exec(select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id))).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    await session.delete(agent)
    await session.commit()
    logger.info("api.agent_deleted", agent_id=agent_id, org_id=org_id)


# ---------------------------------------------------------------------------
# Skills & Apps Attach/Detach
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/skills", response_model=AgentResponse)
async def attach_skill(
    agent_id: str,
    body: dict,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> AgentResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    agent = (await session.exec(select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id).options(selectinload(Agent.skills), selectinload(Agent.app_connections)))).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    skill_id = body.get("skill_id")
    if not skill_id:
        raise HTTPException(status_code=422, detail="Missing skill_id")

    skill = (await session.exec(select(Skill).where(Skill.id == skill_id, Skill.org_id == org_id))).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
        
    if not any(s.id == skill_id for s in agent.skills):
        agent.skills.append(skill)
        session.add(agent)
        await session.commit()
        
    return _agent_to_response(agent)


@router.delete("/{agent_id}/skills/{skill_id}", response_model=AgentResponse)
async def detach_skill(
    agent_id: str,
    skill_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> AgentResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    agent = (await session.exec(select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id).options(selectinload(Agent.skills), selectinload(Agent.app_connections)))).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    agent.skills = [s for s in agent.skills if s.id != skill_id]
    session.add(agent)
    await session.commit()
    
    return _agent_to_response(agent)


@router.post("/{agent_id}/apps", response_model=AgentResponse)
async def attach_app(
    agent_id: str,
    body: dict,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> AgentResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    agent = (await session.exec(select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id).options(selectinload(Agent.skills), selectinload(Agent.app_connections)))).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    connection_id = body.get("connection_id")
    if not connection_id:
        raise HTTPException(status_code=422, detail="Missing connection_id")

    connection = (await session.exec(select(OAuthConnection).where(OAuthConnection.id == connection_id, OAuthConnection.org_id == org_id))).first()
    if not connection:
        raise HTTPException(status_code=404, detail="OAuth connection not found")
        
    if not any(c.id == connection_id for c in agent.app_connections):
        agent.app_connections.append(connection)
        session.add(agent)
        await session.commit()
        
    return _agent_to_response(agent)


@router.delete("/{agent_id}/apps/{connection_id}", response_model=AgentResponse)
async def detach_app(
    agent_id: str,
    connection_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> AgentResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    agent = (await session.exec(select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id).options(selectinload(Agent.skills), selectinload(Agent.app_connections)))).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    agent.app_connections = [c for c in agent.app_connections if c.id != connection_id]
    session.add(agent)
    await session.commit()
    
    return _agent_to_response(agent)


# ---------------------------------------------------------------------------
# Execution (Sync) & Runs
# ---------------------------------------------------------------------------

@router.post("/{agent_id}/execute", response_model=AgentExecuteResponse, status_code=status.HTTP_202_ACCEPTED)
async def execute_agent(
    agent_id: str,
    body: AgentExecuteRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> AgentExecuteResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    
    agent = (await session.exec(
        select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id)
        .options(selectinload(Agent.skills), selectinload(Agent.app_connections))
    )).first()
    
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    # Validate requested skills are attached to this agent
    skills_to_use = []
    if body.skill_ids:
        agent_skill_ids = {s.id for s in agent.skills}
        invalid_skills = set(body.skill_ids) - agent_skill_ids
        if invalid_skills:
             raise HTTPException(status_code=400, detail=f"Skills not attached to agent: {invalid_skills}")
        
        # Load the skill objects to get instructions
        skills_to_use = [s for s in agent.skills if s.id in body.skill_ids]
        
    prompt = build_prompt(agent, skills_to_use, body.input)
    
    run_record = AgentRun(
        org_id=org_id,
        agent_id=agent.id,
        triggered_by=AgentRunTriggeredBy(body.triggered_by),
        source_id=body.source_id,
        skill_ids=json.dumps(body.skill_ids) if body.skill_ids else "[]",
        input_json=json.dumps(body.input),
        prompt_used=prompt,
        status=AgentRunStatus.RUNNING,
    )
    session.add(run_record)
    await session.commit()
    
    # Execute LLM inline synchronously
    try:
        from litellm import acompletion
        
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
            
        # litellm expects messages list
        messages = [
            {"role": "user", "content": prompt}
        ]
        
        resolved_model = _resolve_model(agent.model)
        
        response = await acompletion(
            model=resolved_model,
            messages=messages,
            timeout=agent.timeout_seconds,
        )
        
        output_content = response.choices[0].message.content
        
        run_record.status = AgentRunStatus.COMPLETED
        run_record.output = output_content
        import datetime
        run_record.completed_at = datetime.datetime.now(datetime.timezone.utc)
        
    except Exception as e:
        logger.error("agent_execution_failed", error=str(e), agent_id=agent.id, run_id=run_record.id)
        run_record.status = AgentRunStatus.FAILED
        run_record.error_message = str(e)
        import datetime
        run_record.completed_at = datetime.datetime.now(datetime.timezone.utc)
        
    session.add(run_record)
    await session.commit()
    
    return AgentExecuteResponse(
        run_id=run_record.id,
        status=run_record.status.value if hasattr(run_record.status, "value") else run_record.status,
        output=run_record.output,
        error=run_record.error_message
    )


@router.get("/{agent_id}/runs", response_model=AgentRunListResponse)
async def list_agent_runs(
    agent_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AgentRunListResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    
    query = select(AgentRun).where(AgentRun.org_id == org_id, AgentRun.agent_id == agent_id).order_by(AgentRun.started_at.desc())
    
    count_query = select(func.count()).select_from(
        select(AgentRun.id).where(AgentRun.org_id == org_id, AgentRun.agent_id == agent_id).subquery()
    )
    total = (await session.exec(count_query)).one()
    
    offset = (page - 1) * page_size
    runs = (await session.exec(query.offset(offset).limit(page_size))).all()
    
    items = []
    for run in runs:
        items.append(AgentRunResponse(
            id=run.id,
            agent_id=run.agent_id,
            triggered_by=run.triggered_by.value if hasattr(run.triggered_by, "value") else run.triggered_by,
            status=run.status.value if hasattr(run.status, "value") else run.status,
            created_at=run.started_at,
            completed_at=run.completed_at,
        ))
        
    return AgentRunListResponse(
        items=items,
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        ),
    )


@router.get("/{agent_id}/runs/{run_id}", response_model=AgentRunDetailResponse)
async def get_agent_run(
    agent_id: str,
    run_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> AgentRunDetailResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    
    run = (await session.exec(select(AgentRun).where(AgentRun.id == run_id, AgentRun.agent_id == agent_id, AgentRun.org_id == org_id))).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
        
    skill_ids_list = []
    try:
        skill_ids_list = json.loads(run.skill_ids) if run.skill_ids else []
    except Exception:
        pass
        
    return AgentRunDetailResponse(
        id=run.id,
        agent_id=run.agent_id,
        triggered_by=run.triggered_by.value if hasattr(run.triggered_by, "value") else run.triggered_by,
        status=run.status.value if hasattr(run.status, "value") else run.status,
        created_at=run.started_at,
        completed_at=run.completed_at,
        skill_ids=skill_ids_list,
        input_json=run.input_json,
        prompt_used=run.prompt_used,
        output=run.output,
        error_message=run.error_message,
    )

