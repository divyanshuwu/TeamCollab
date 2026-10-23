from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, func, ForeignKey, UniqueConstraint
from database import Base
from sqlalchemy.orm import relationship


class ProjectDB(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    owner_id= Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )


class UserDB(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    auth_user_id = Column(String(36), nullable=True, unique=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


class ProjectMemberDB(Base):
    __tablename__ = "project_members"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_project_member",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
    )

    role = Column(String(20), nullable=False, default="member")

    joined_at = Column(
        DateTime,
        server_default=func.now(),
    )


class TaskDB(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)

    status = Column(
        String(20),
        nullable=False,
        default="todo",
    )

    priority = Column(
        String(20),
        nullable=False,
        default="medium",
    )

    project_id = Column(
        Integer,
        ForeignKey("projects.id"),
        nullable=False,
    )

    assigned_to = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
    )

    due_date = Column(DateTime, nullable=True)

    created_at = Column(
        DateTime,
        server_default=func.now(),
    )