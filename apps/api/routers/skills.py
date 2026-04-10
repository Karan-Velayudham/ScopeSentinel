from typing import Annotated
import structlog
from fastapi import APIRouter, HTTPException, Query, status, Request
from sqlmodel import select, func
import datetime

from auth.api_keys import CurrentUserDep
from db.models import Skill
from db.session import TenantSessionDep
from schemas import (
    PaginationMeta,
    SkillCreateRequest,
    SkillUpdateRequest,
    SkillResponse,
    SkillListResponse,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/skills", tags=["skills"])

def _skill_to_response(skill: Skill) -> SkillResponse:
    return SkillResponse(
        id=skill.id,
        org_id=skill.org_id,
        name=skill.name,
        description=skill.description,
        instructions=skill.instructions,
        version=skill.version,
        is_active=skill.is_active,
        created_at=skill.created_at,
        updated_at=skill.updated_at,
    )

@router.post("/", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
async def create_skill(
    body: SkillCreateRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> SkillResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    skill = Skill(
        org_id=org_id,
        name=body.name,
        description=body.description,
        instructions=body.instructions,
        is_active=body.is_active,
    )
    session.add(skill)
    await session.commit()
    
    logger.info("api.skill_created", skill_id=skill.id, org_id=org_id)
    return _skill_to_response(skill)

@router.get("/", response_model=SkillListResponse)
async def list_skills(
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SkillListResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    query = select(Skill).where(Skill.org_id == org_id).order_by(Skill.created_at.desc())
    
    count_query = select(func.count()).select_from(
        select(Skill).where(Skill.org_id == org_id).subquery()
    )
    total = (await session.exec(count_query)).one()
    
    offset = (page - 1) * page_size
    skills = (await session.exec(query.offset(offset).limit(page_size))).all()
    
    return SkillListResponse(
        items=[_skill_to_response(s) for s in skills],
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        ),
    )

@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(
    skill_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> SkillResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    skill = (await session.exec(select(Skill).where(Skill.id == skill_id, Skill.org_id == org_id))).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return _skill_to_response(skill)

@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: str,
    body: SkillUpdateRequest,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> SkillResponse:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    skill = (await session.exec(select(Skill).where(Skill.id == skill_id, Skill.org_id == org_id))).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
        
    has_changes = False
    
    if body.name is not None:
        skill.name = body.name
        has_changes = True
    if body.description is not None:
        skill.description = body.description
        has_changes = True
    if body.instructions is not None:
        skill.instructions = body.instructions
        has_changes = True
    if body.is_active is not None:
        skill.is_active = body.is_active
        has_changes = True
        
    if has_changes:
        skill.version += 1
        skill.updated_at = datetime.datetime.now(datetime.timezone.utc)
        session.add(skill)
        await session.commit()
        logger.info("api.skill_updated", skill_id=skill.id, org_id=org_id)
        
    return _skill_to_response(skill)

@router.delete("/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_skill(
    skill_id: str,
    session: TenantSessionDep,
    current_user: CurrentUserDep,
    request: Request,
) -> None:
    org_id = getattr(request.state, "org_id", None) or current_user.org_id
    skill = (await session.exec(select(Skill).where(Skill.id == skill_id, Skill.org_id == org_id))).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    
    await session.delete(skill)
    await session.commit()
    logger.info("api.skill_deleted", skill_id=skill_id, org_id=org_id)
