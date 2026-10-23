
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import case, func

from database import get_db
from models import ProjectDB, TaskDB, UserDB
from schemas import ProjectCreate, ProjectResponse
from routers.auth import get_current_user

router = APIRouter(
    prefix="/projects",
    tags=["Projects"]
)


@router.post("/", response_model=ProjectResponse, status_code=201)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user)
):
    new_project = ProjectDB(
        name=project.name,
        description=project.description,
        owner_id=current_user.id
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project



@router.get("/", response_model=list[ProjectResponse])
def get_projects(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    return (
        db.query(ProjectDB)
        .filter(ProjectDB.owner_id == current_user.id)
        .all()
    )


@router.get("/summary")
def get_owned_task_summary(
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    result = (
        db.query(
            func.count(TaskDB.id).label("total_tasks"),
            func.coalesce(func.sum(case((TaskDB.status == "todo", 1), else_=0)), 0).label("todo"),
            func.coalesce(func.sum(case((TaskDB.status == "in_progress", 1), else_=0)), 0).label("in_progress"),
            func.coalesce(func.sum(case((TaskDB.status == "done", 1), else_=0)), 0).label("done"),
        )
        .join(ProjectDB, ProjectDB.id == TaskDB.project_id)
        .filter(ProjectDB.owner_id == current_user.id)
        .one()
    )
    return {
        "total_tasks": result.total_tasks,
        "todo": result.todo,
        "in_progress": result.in_progress,
        "done": result.done,
    }


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    project = (
        db.query(ProjectDB)
        .filter(
            ProjectDB.id == project_id,
            ProjectDB.owner_id == current_user.id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    project = (
        db.query(ProjectDB)
        .filter(
            ProjectDB.id == project_id,
            ProjectDB.owner_id == current_user.id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    project.name = project_data.name
    project.description = project_data.description

    db.commit()
    db.refresh(project)

    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    project = (
        db.query(ProjectDB)
        .filter(
            ProjectDB.id == project_id,
            ProjectDB.owner_id == current_user.id,
        )
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    db.delete(project)
    db.commit()

    return {"message": "Project deleted successfully"}