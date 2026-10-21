from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import ProjectDB, ProjectMemberDB, UserDB
from schemas import ProjectMemberCreate, ProjectMemberResponse
from routers.auth import get_current_user

router = APIRouter(
    prefix="/projects",
    tags=["Project Members"],
)

@router.post("/{project_id}/members", status_code=201)
def add_project_member(
    project_id: int,
    member_data: ProjectMemberCreate,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    # Check whether the project exists and belongs to the logged-in user
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

    # Check whether the user to add exists
    member = (
        db.query(UserDB)
        .filter(UserDB.id == member_data.user_id)
        .first()
    )

    if member is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    # Only allow the member role for now
    if member_data.role != "member":
        raise HTTPException(
            status_code=400,
            detail="Only the member role is allowed",
        )

    # Prevent duplicate memberships
    existing_membership = (
        db.query(ProjectMemberDB)
        .filter(
            ProjectMemberDB.project_id == project_id,
            ProjectMemberDB.user_id == member_data.user_id,
        )
        .first()
    )

    if existing_membership:
        raise HTTPException(
            status_code=409,
            detail="User is already a member of this project",
        )

    new_membership = ProjectMemberDB(
        project_id=project_id,
        user_id=member_data.user_id,
        role="member",
    )

    db.add(new_membership)
    db.commit()
    db.refresh(new_membership)

    return {
        "message": "Member added successfully",
        "project_id": new_membership.project_id,
        "user_id": new_membership.user_id,
        "role": new_membership.role,
    }


@router.get("/{project_id}/members", response_model=list[ProjectMemberResponse])
def get_project_members(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    # Check that the project exists
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

    # Check that the current user owns or belongs to the project
    is_owner = project.owner_id == current_user.id

    is_member = (
        db.query(ProjectMemberDB)
        .filter(
            ProjectMemberDB.project_id == project_id,
            ProjectMemberDB.user_id == current_user.id,
        )
        .first()
    )

    if not is_owner and not is_member:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this project",
        )

    # Return the project's members with their user details
    members = (
        db.query(
            UserDB.id.label("user_id"),
            UserDB.name,
            UserDB.email,
            ProjectMemberDB.role,
        )
        .join(
            ProjectMemberDB,
            ProjectMemberDB.user_id == UserDB.id,
        )
        .filter(ProjectMemberDB.project_id == project_id)
        .all()
    )

    return members


@router.delete("/{project_id}/members/{user_id}")
def remove_project_member(
    project_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: UserDB = Depends(get_current_user),
):
    # Check that the project belongs to the logged-in user
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

    # Find the membership
    membership = (
        db.query(ProjectMemberDB)
        .filter(
            ProjectMemberDB.project_id == project_id,
            ProjectMemberDB.user_id == user_id,
        )
        .first()
    )

    if membership is None:
        raise HTTPException(
            status_code=404,
            detail="Project member not found",
        )

    db.delete(membership)
    db.commit()

    return {"message": "Project member removed successfully"}