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
    WorkflowActivateResponse,
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
        status=getattr(wf, 'status', 'draft'),
        yaml_content=wf.yaml_content,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
    )

@router.get("/templates", response_model=list[WorkflowResponse])
async def get_templates(current_user: CurrentUserDep):  # FIX M-3: added auth guard
    """Return static out-of-the-box workflow templates. FIX M-4: 5 templates."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    templates = [
        WorkflowResponse(
            id="tmpl-1",
            org_id="system",
            name="Jira to PR Pipeline",
            description="Reads a Jira ticket, plans an implementation, generates code, and opens a GitHub PR.",
            version=1,
            yaml_content="name: Jira to PR Pipeline\ntrigger:\n  type: jira\n  event: issue_created\nsteps:\n  - id: plan\n    type: agent\n    name: Planner\n    inputs:\n      model: gpt-4o\n  - id: code\n    type: agent\n    name: Coder\n    inputs:\n      model: gpt-4o\n  - id: hitl_review\n    type: hitl\n    name: Review Plan\n    next: [code]\n",
            created_at=now,
            updated_at=now,
        ),
        WorkflowResponse(
            id="tmpl-2",
            org_id="system",
            name="Build Failure Triager",
            description="Triggered by a CI failure event. Analyses build logs and proposes a fix as a PR.",
            version=1,
            yaml_content="name: Build Failure Triager\ntrigger:\n  type: datadog\n  event: build_failure\nsteps:\n  - id: analyse\n    type: agent\n    name: Log Analyser\n  - id: patch\n    type: agent\n    name: Patcher\n",
            created_at=now,
            updated_at=now,
        ),
        WorkflowResponse(
            id="tmpl-3",
            org_id="system",
            name="PR Review Agent",
            description="Automatically reviews open pull requests for code quality, security, and style issues.",
            version=1,
            yaml_content="name: PR Review Agent\ntrigger:\n  type: github\n  event: pull_request.opened\nsteps:\n  - id: review\n    type: agent\n    name: Reviewer\n    inputs:\n      model: gpt-4o\n  - id: comment\n    type: tool\n    name: Post GitHub Comment\n",
            created_at=now,
            updated_at=now,
        ),
        WorkflowResponse(
            id="tmpl-4",
            org_id="system",
            name="Incident Responder",
            description="Triggered by a PagerDuty alert. Creates a Jira incident ticket and posts a Slack triage thread.",
            version=1,
            yaml_content="name: Incident Responder\ntrigger:\n  type: webhook\n  source: pagerduty\nsteps:\n  - id: create_ticket\n    type: tool\n    name: Create Jira Issue\n  - id: notify_slack\n    type: tool\n    name: Slack Notification\n",
            created_at=now,
            updated_at=now,
        ),
        WorkflowResponse(
            id="tmpl-5",
            org_id="system",
            name="Deploy Validator",
            description="Runs post-deploy checks after a GitHub Actions deployment completes successfully.",
            version=1,
            yaml_content="name: Deploy Validator\ntrigger:\n  type: github\n  event: workflow_run.completed\nsteps:\n  - id: smoke_test\n    type: agent\n    name: Smoke Tester\n  - id: notify\n    type: tool\n    name: Slack Notification\n",
            created_at=now,
            updated_at=now,
        ),
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


@router.post("/{workflow_id}/activate", response_model=WorkflowActivateResponse)
async def activate_workflow(
    workflow_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> WorkflowActivateResponse:
    """Activate a workflow to make it a trigger listener."""
    wf = (await session.exec(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.org_id == current_user.org_id)
    )).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    wf.status = "active"
    session.add(wf)
    await session.commit()
    logger.info("workflow.activated", workflow_id=workflow_id)
    return WorkflowActivateResponse(id=wf.id, status="active")


@router.post("/{workflow_id}/deactivate", response_model=WorkflowActivateResponse)
async def deactivate_workflow(
    workflow_id: str,
    session: SessionDep,
    current_user: CurrentUserDep,
) -> WorkflowActivateResponse:
    """Pause an active workflow."""
    wf = (await session.exec(
        select(Workflow).where(Workflow.id == workflow_id, Workflow.org_id == current_user.org_id)
    )).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    wf.status = "paused"
    session.add(wf)
    await session.commit()
    logger.info("workflow.deactivated", workflow_id=workflow_id)
    return WorkflowActivateResponse(id=wf.id, status="paused")
