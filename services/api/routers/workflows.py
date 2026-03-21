import yaml
from typing import Annotated, Optional
import structlog
from fastapi import APIRouter, HTTPException, Query, status, Response, File, UploadFile
from sqlmodel import select

from auth.api_keys import CurrentUserDep
from db.models import Workflow
from db.session import SessionDep
from schemas import (
    PaginationMeta,
    WorkflowCreateRequest,
    WorkflowUpdateRequest,
    WorkflowResponse,
    WorkflowListResponse,
    WorkflowDSL,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

def _validate_yaml_dsl(yaml_str: str) -> None:
    try:
        data = yaml.safe_load(yaml_str)
    except yaml.YAMLError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid YAML format: {exc}",
        )
    
    # Use Pydantic to validate the structure
    try:
        WorkflowDSL(**data)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"YAML content is structurally invalid according to WorkflowDSL: {exc}",
        )

def _workflow_to_response(wf: Workflow) -> WorkflowResponse:
    return WorkflowResponse(
        id=wf.id,
        org_id=wf.org_id,
        name=wf.name,
        description=wf.description,
        version=wf.version,
        yaml_content=wf.yaml_content,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
    )

@router.get("/templates", response_model=list[WorkflowResponse])
async def get_templates():
    """Return static out-of-the-box workflow templates."""
    # Dummy template list to satisfy Epic 3.3.3
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)
    
    templates = [
        WorkflowResponse(
            id="tmpl-1",
            org_id="system",
            name="Jira to PR Pipeline",
            description="Reads Jira ticket, plans, codes, and pushes a PR.",
            version=1,
            yaml_content="name: Jira to PR Pipeline\ntrigger:\n  type: github\nsteps:\n  - id: 1\n    type: agent\n    name: planner\n",
            created_at=now,
            updated_at=now,
        ),
        WorkflowResponse(
            id="tmpl-2",
            org_id="system",
            name="Build Failure Triager",
            description="Analyzes build logs and proposes a fix.",
            version=1,
            yaml_content="name: Build Failure Triager\ntrigger:\n  type: datadog\nsteps: []\n",
            created_at=now,
            updated_at=now,
        )
    ]
    return templates

@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def create_workflow(
    body: WorkflowCreateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> WorkflowResponse:
    _validate_yaml_dsl(body.yaml_content)
    
    wf = Workflow(
        org_id=current_user.org_id,
        name=body.name,
        description=body.description,
        yaml_content=body.yaml_content,
        version=1,
    )
    session.add(wf)
    await session.commit()
    await session.refresh(wf)
    
    logger.info("api.workflow_created", workflow_id=wf.id)
    return _workflow_to_response(wf)

@router.get("/", response_model=WorkflowListResponse)
async def list_workflows(
    session: SessionDep,
    current_user: CurrentUserDep,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> WorkflowListResponse:
    query = select(Workflow).where(Workflow.org_id == current_user.org_id).order_by(Workflow.created_at.desc())
    
    from sqlalchemy import func
    count_query = select(func.count()).select_from(
        select(Workflow).where(Workflow.org_id == current_user.org_id).subquery()
    )
    total = (await session.exec(count_query)).one()
    
    offset = (page - 1) * page_size
    runs = (await session.exec(query.offset(offset).limit(page_size))).all()
    
    return WorkflowListResponse(
        items=[_workflow_to_response(r) for r in runs],
        meta=PaginationMeta(
            total=total,
            page=page,
            page_size=page_size,
            has_next=(offset + page_size) < total,
        ),
    )

@router.get("/{workflow_id}", response_model=WorkflowResponse)
async def get_workflow(
    workflow_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> WorkflowResponse:
    wf = (await session.exec(select(Workflow).where(Workflow.id == workflow_id, Workflow.org_id == current_user.org_id))).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return _workflow_to_response(wf)

@router.put("/{workflow_id}", response_model=WorkflowResponse)
async def update_workflow(
    workflow_id: str,
    body: WorkflowUpdateRequest,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> WorkflowResponse:
    wf = (await session.exec(select(Workflow).where(Workflow.id == workflow_id, Workflow.org_id == current_user.org_id))).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
        
    has_changes = False
    
    if body.yaml_content is not None and body.yaml_content != wf.yaml_content:
        _validate_yaml_dsl(body.yaml_content)
        wf.yaml_content = body.yaml_content
        wf.version += 1
        has_changes = True

    if body.name is not None and body.name != wf.name:
        wf.name = body.name
        has_changes = True
        
    if body.description is not None and body.description != wf.description:
        wf.description = body.description
        has_changes = True
        
    if has_changes:
        import datetime
        wf.updated_at = datetime.datetime.now(datetime.timezone.utc)
        session.add(wf)
        await session.commit()
        await session.refresh(wf)
        logger.info("api.workflow_updated", workflow_id=wf.id, version=wf.version)
        
    return _workflow_to_response(wf)

@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workflow(
    workflow_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> None:
    wf = (await session.exec(select(Workflow).where(Workflow.id == workflow_id, Workflow.org_id == current_user.org_id))).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    await session.delete(wf)
    await session.commit()
    logger.info("api.workflow_deleted", workflow_id=workflow_id)

@router.post("/import", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
async def import_workflow(
    session: SessionDep,
    current_user: CurrentUserDep,
    file: UploadFile = File(...),
) -> WorkflowResponse:
    """Import a YAML file as a new Workflow."""
    content = await file.read()
    yaml_str = content.decode("utf-8")
    
    _validate_yaml_dsl(yaml_str)
    
    # Generate name from file or use a default
    name = file.filename or "Imported Workflow"
    if name.endswith(".yaml") or name.endswith(".yml"):
        name = name.rsplit(".", 1)[0]
    
    wf = Workflow(
        org_id=current_user.org_id,
        name=name,
        yaml_content=yaml_str,
        version=1,
    )
    session.add(wf)
    await session.commit()
    await session.refresh(wf)
    
    logger.info("api.workflow_imported", workflow_id=wf.id)
    return _workflow_to_response(wf)

@router.get("/{workflow_id}/export")
async def export_workflow(
    workflow_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> Response:
    wf = (await session.exec(select(Workflow).where(Workflow.id == workflow_id, Workflow.org_id == current_user.org_id))).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return Response(
        content=wf.yaml_content,
        media_type="application/x-yaml",
        headers={"Content-Disposition": f"attachment; filename={wf.name.replace(' ', '_')}.yaml"}
    )
