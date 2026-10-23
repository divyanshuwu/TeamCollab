from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, case

from database import get_db
from models import TaskDB, ProjectDB, ProjectMemberDB, UserDB
from schemas import TaskCreate, TaskResponse, TaskStatusUpdate, TaskUpdate
from routers.auth import enforce_user_rate_limit, get_current_user

router = APIRouter(
    prefix="/projects",
    tags=["Tasks"],
    dependencies=[Depends(enforce_user_rate_limit)],
)


def check_project_access(
    project_id: int,
    current_user: UserDB,
    db: Session,
):
    project = (
        db.query(ProjectDB)
        .filter(ProjectDB.id == project_id)
        .first()
    )

    if project is None:
        raise HTTPException(
            status_code=404,
            detail="Project not found",
        )

    is_owner = project.owner_id == current_user.id

    is_member = (
        db.query(ProjectMemberDB)
        .filter(
            ProjectMemberDB.project_id == project_id,
            ProjectMemberDB.user_id == current_user.id,
        )
        .first()
        is not None
    )

    if not is_owner and not is_member:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project",
        )

    return project


@router.post(
    "/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=201,
)
def create_task(
    project_id: int,
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    # Verify project access
    check_project_access(project_id, current_user, db)

    # Validate the assigned user, if provided
    if task_data.assigned_to is not None:
        assigned_user = (
            db.query(UserDB)
            .filter(UserDB.id == task_data.assigned_to)
            .first()
        )

        if assigned_user is None:
            raise HTTPException(
                status_code=404,
                detail="Assigned user not found",
            )

        # The assignee must belong to this project
        is_assignee_member = (
            db.query(ProjectMemberDB)
            .filter(
                ProjectMemberDB.project_id == project_id,
                ProjectMemberDB.user_id == task_data.assigned_to,
            )
            .first()
            is not None
        )

        project = (
            db.query(ProjectDB)
            .filter(ProjectDB.id == project_id)
            .first()
        )

        if (
            task_data.assigned_to != project.owner_id
            and not is_assignee_member
        ):
            raise HTTPException(
                status_code=400,
                detail="Assignee must belong to this project",
            )

    new_task = TaskDB(
        title=task_data.title,
        description=task_data.description,
        priority=task_data.priority,
        assigned_to=task_data.assigned_to,
        due_date=task_data.due_date,
        project_id=project_id,
        status="todo",
    )

    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    return new_task



@router.get(
    "/{project_id}/tasks",
    response_model=list[TaskResponse],
)
def get_project_tasks(
    project_id: int,
    status: str | None = Query(
        default=None,
        pattern="^(todo|in_progress|done)$",
    ),
    priority: str | None = Query(
        default=None,
        pattern="^(low|medium|high)$",
    ),
    sort_order: str = Query(
        default="newest",
        pattern="^(newest|oldest)$",
    ),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    check_project_access(project_id, current_user, db)

    query = db.query(TaskDB).filter(
        TaskDB.project_id == project_id
    )

    if status is not None:
        query = query.filter(TaskDB.status == status)

    if priority is not None:
        query = query.filter(TaskDB.priority == priority)

    if sort_order == "newest":
        query = query.order_by(TaskDB.created_at.desc())
    else:
        query = query.order_by(TaskDB.created_at.asc())

    return query.offset(skip).limit(limit).all()



@router.patch(
    "/{project_id}/tasks/{task_id}/status",
    response_model=TaskResponse,
)
def update_task_status(
    project_id: int,
    task_id: int,
    status_data: TaskStatusUpdate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    check_project_access(project_id, current_user, db)

    task = (
        db.query(TaskDB)
        .filter(
            TaskDB.id == task_id,
            TaskDB.project_id == project_id,
        )
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    task.status = status_data.status

    db.commit()
    db.refresh(task)

    return task



@router.delete(
    "/{project_id}/tasks/{task_id}",
    status_code=204,
)
def delete_task(
    project_id: int,
    task_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    check_project_access(project_id, current_user, db)

    task = (
        db.query(TaskDB)
        .filter(
            TaskDB.id == task_id,
            TaskDB.project_id == project_id,
        )
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    db.delete(task)
    db.commit()




@router.put(
    "/{project_id}/tasks/{task_id}",
    response_model=TaskResponse,
)
def update_task(
    project_id: int,
    task_id: int,
    task_data: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    check_project_access(project_id, current_user, db)

    task = (
        db.query(TaskDB)
        .filter(
            TaskDB.id == task_id,
            TaskDB.project_id == project_id,
        )
        .first()
    )

    if task is None:
        raise HTTPException(
            status_code=404,
            detail="Task not found",
        )

    if task_data.assigned_to is not None:
        is_owner = (
            db.query(ProjectDB)
            .filter(
                ProjectDB.id == project_id,
                ProjectDB.owner_id == task_data.assigned_to,
            )
            .first()
            is not None
        )

        is_member = (
            db.query(ProjectMemberDB)
            .filter(
                ProjectMemberDB.project_id == project_id,
                ProjectMemberDB.user_id == task_data.assigned_to,
            )
            .first()
            is not None
        )

        if not is_owner and not is_member:
            raise HTTPException(
                status_code=400,
                detail="Assigned user must be a project owner or member",
            )

    task.title = task_data.title
    task.description = task_data.description
    task.priority = task_data.priority
    task.assigned_to = task_data.assigned_to
    task.due_date = task_data.due_date

    db.commit()
    db.refresh(task)

    return task




@router.get("/{project_id}/tasks/summary")
def get_task_summary(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    check_project_access(project_id, current_user, db)

    result = (
        db.query(
            func.count(TaskDB.id).label("total_tasks"),
            func.sum(
                case((TaskDB.status == "todo", 1), else_=0)
            ).label("todo"),
            func.sum(
                case((TaskDB.status == "in_progress", 1), else_=0)
            ).label("in_progress"),
            func.sum(
                case((TaskDB.status == "done", 1), else_=0)
            ).label("done"),
        )
        .filter(TaskDB.project_id == project_id)
        .one()
    )

    return {
        "project_id": project_id,
        "total_tasks": result.total_tasks,
        "todo": result.todo or 0,
        "in_progress": result.in_progress or 0,
        "done": result.done or 0,
    }
