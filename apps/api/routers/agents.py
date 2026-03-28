import json
from typing import Annotated, Optional
import structlog
from fastapi import APIRouter, HTTPException, Query, status, Request
from sqlmodel import select, func

from sqlalchemy.orm import selectinload
from auth.api_keys import CurrentUserDep
from db.models import Agent, Skill, AgentSkillLink
from db.session import TenantSessionDep
from schemas import (
    PaginationMeta,
    AgentCreateRequest,
    AgentUpdateRequest,
    AgentResponse,
    AgentListResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])

def _agent_to_response(agent: Agent, skills: Optional[list[Skill]] = None) -> AgentResponse:
    tools = []
    try:
        tools = json.loads(agent.tools_json)
    except Exception:
        pass
    
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

    return AgentResponse(
        id=agent.id,
        org_id=agent.org_id,
        name=agent.name,
        description=agent.description,
        identity=agent.identity,
        model=agent.model,
        tools=tools,
        skills=skill_ids,
        max_iterations=agent.max_iterations,
        memory_mode=agent.memory_mode,
        is_active=agent.is_active,
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
        identity=body.identity,
        model=body.model,
        tools_json=json.dumps(body.tools),
        max_iterations=body.max_iterations,
        memory_mode=body.memory_mode,
    )
    
    if body.skills:
        # Resolve skills for the org
        skills = (await session.exec(select(Skill).where(Skill.org_id == org_id, Skill.id.in_(body.skills)))).all()
        agent.skills = skills

    session.add(agent)
    await session.commit()
    # Skip refresh to avoid potential 500 during session-persisted refresh
    
    logger.info("api.agent_created", agent_id=agent.id, org_id=org_id)
    return _agent_to_response(agent, skills=skills if body.skills else [])

@router.get("/", response_model=AgentListResponse)
async def list_agents(
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> AgentListResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    query = select(Agent).where(Agent.org_id == org_id).options(selectinload(Agent.skills)).order_by(Agent.created_at.desc())
    
    count_query = select(func.count()).select_from(
        select(Agent).where(Agent.org_id == org_id).subquery()
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
    agent = (await session.exec(select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id))).first()
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
    agent = (await session.exec(select(Agent).where(Agent.id == agent_id, Agent.org_id == org_id))).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    has_changes = False
    
    if body.name is not None:
        agent.name = body.name
        has_changes = True
    if body.description is not None:
        agent.description = body.description
        has_changes = True
    if body.identity is not None:
        agent.identity = body.identity
        has_changes = True
    if body.model is not None:
        agent.model = body.model
        has_changes = True
    if body.tools is not None:
        agent.tools_json = json.dumps(body.tools)
        has_changes = True
    if body.skills is not None:
        # Update skills many-to-many
        skills = (await session.exec(select(Skill).where(Skill.org_id == org_id, Skill.id.in_(body.skills)))).all()
        agent.skills = list(skills)
        has_changes = True
    if body.max_iterations is not None:
        agent.max_iterations = body.max_iterations
        has_changes = True
    if body.memory_mode is not None:
        agent.memory_mode = body.memory_mode
        has_changes = True
    if body.is_active is not None:
        agent.is_active = body.is_active
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
