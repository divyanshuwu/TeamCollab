from uuid import uuid4
from models import UserDB
from security import verify_password

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from main import app
from database import Base, database_url, get_db
import models


# Create a separate engine for automated tests
test_database_url = database_url.set(
    database="teamcollab_tests"
)

test_engine = create_engine(test_database_url)

TestSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


# Create tables in the test database
Base.metadata.create_all(bind=test_engine)


# Give the API a test database session
def override_get_db():
    db = TestSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_home():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "Welcome to TeamCollab API"
    }



def test_register_user():
    email = f"test_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    response = client.post(
        "/auth/register",
        json={
            "name": "Test User",
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test User"
    assert data["email"] == email
    assert "password" not in data
    assert "password_hash" not in data

    # Verify the user was saved in the test database
    db = TestSessionLocal()
    try:
        user = db.query(UserDB).filter(
            UserDB.email == email
        ).first()

        assert user is not None
        assert user.password_hash != password
        assert verify_password(password, user.password_hash)
    finally:
        db.close()



def test_login_user():
    from uuid import uuid4

    email = f"login_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register a new user first
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Login Test User",
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201

    # Log in with the registered user's credentials
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


def test_login_wrong_password():
    from uuid import uuid4

    email = f"wrong_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register a new user
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Wrong Password Test",
            "email": email,
            "password": password,
        },
    )

    assert register_response.status_code == 201

    # Attempt login with an incorrect password
    response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401



def test_get_current_user():
    from uuid import uuid4

    email = f"me_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register a user
    client.post(
        "/auth/register",
        json={
            "name": "Current User Test",
            "email": email,
            "password": password,
        },
    )

    # Log in to obtain a token
    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # Request the current user's information
    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Current User Test"
    assert data["email"] == email
    assert "password" not in data
    assert "password_hash" not in data


def test_get_current_user_without_token():
    response = client.get("/auth/me")

    assert response.status_code == 401



def test_user_cannot_access_another_users_project():
    from uuid import uuid4

    # Create two different users
    unique_id = uuid4().hex[:8]
    owner_email = f"owner_{unique_id}@example.com"
    other_email = f"other_{unique_id}@example.com"
    password = "TestPassword123!"

    for name, email in [
        ("Project Owner", owner_email),
        ("Other User", other_email),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
            },
        )
        assert response.status_code == 201

    # Log in as the project owner
    owner_login = client.post(
        "/auth/login",
        json={
            "email": owner_email,
            "password": password,
        },
    )
    owner_token = owner_login.json()["access_token"]

    # Log in as the other user
    other_login = client.post(
        "/auth/login",
        json={
            "email": other_email,
            "password": password,
        },
    )
    other_token = other_login.json()["access_token"]

    # Owner creates a project
    project_response = client.post(
        "/projects/",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "name": "Private Test Project",
            "description": "Testing project privacy",
        },
    )

    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    # The other user attempts to access the project
    response = client.get(
        f"/projects/{project_id}",
        headers={"Authorization": f"Bearer {other_token}"},
    )

    assert response.status_code == 404



def test_create_project_without_name():
    from uuid import uuid4

    email = f"project_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register a user
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Project Test User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    # Log in
    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    # Attempt to create a project without its required name
    response = client.post(
        "/projects/",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "description": "This project has no name"
        },
    )

    assert response.status_code == 422



def test_create_task():
    from uuid import uuid4

    email = f"task_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register a user
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Task Test User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    # Log in
    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Task Test Project",
            "description": "Project for testing tasks",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Create a task
    task_response = client.post(
        f"/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Complete API testing",
            "description": "Test task creation",
        },
    )

    assert task_response.status_code == 201

    task = task_response.json()

    assert task["title"] == "Complete API testing"
    assert task["description"] == "Test task creation"
    assert task["project_id"] == project_id
    assert task["status"] == "todo"
    assert task["priority"] == "medium"



def test_update_task_status():
    from uuid import uuid4

    email = f"status_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register a user
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Status Test User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    # Log in
    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Status Test Project",
            "description": "Testing task status updates",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Create a task
    task_response = client.post(
        f"/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Test status update",
        },
    )
    assert task_response.status_code == 201

    task_id = task_response.json()["id"]

    # Update task status
    response = client.patch(
        f"/projects/{project_id}/tasks/{task_id}/status",
        headers=headers,
        json={"status": "in_progress"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"



def test_filter_tasks_by_status():
    from uuid import uuid4

    email = f"filter_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register and log in
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Filter Test User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Filter Test Project",
            "description": "Testing task filtering",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Create two tasks
    for title in ["Task One", "Task Two"]:
        response = client.post(
            f"/projects/{project_id}/tasks",
            headers=headers,
            json={"title": title},
        )
        assert response.status_code == 201

    # Change Task Two to in_progress
    tasks_response = client.get(
        f"/projects/{project_id}/tasks",
        headers=headers,
    )
    assert tasks_response.status_code == 200

    tasks = tasks_response.json()
    task_two = next(
        task for task in tasks
        if task["title"] == "Task Two"
    )

    update_response = client.patch(
        f"/projects/{project_id}/tasks/{task_two['id']}/status",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert update_response.status_code == 200

    # Retrieve only todo tasks
    response = client.get(
        f"/projects/{project_id}/tasks?status=todo",
        headers=headers,
    )

    assert response.status_code == 200

    filtered_tasks = response.json()
    assert len(filtered_tasks) == 1
    assert filtered_tasks[0]["title"] == "Task One"
    assert filtered_tasks[0]["status"] == "todo"




def test_delete_task():
    from uuid import uuid4

    email = f"delete_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register a user
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Delete Test User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    # Log in
    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Delete Test Project",
            "description": "Testing task deletion",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Create a task
    task_response = client.post(
        f"/projects/{project_id}/tasks",
        headers=headers,
        json={"title": "Task to delete"},
    )
    assert task_response.status_code == 201

    task_id = task_response.json()["id"]

    # Delete the task
    delete_response = client.delete(
        f"/projects/{project_id}/tasks/{task_id}",
        headers=headers,
    )
    assert delete_response.status_code == 204

    # Confirm the task is no longer in the list
    list_response = client.get(
        f"/projects/{project_id}/tasks",
        headers=headers,
    )
    assert list_response.status_code == 200

    remaining_tasks = list_response.json()
    assert all(task["id"] != task_id for task in remaining_tasks)



def test_task_summary():
    from uuid import uuid4

    email = f"summary_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register a user
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Summary Test User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    # Log in
    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Summary Test Project",
            "description": "Testing task summary",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Create three tasks
    task_ids = []

    for title in ["Task One", "Task Two", "Task Three"]:
        response = client.post(
            f"/projects/{project_id}/tasks",
            headers=headers,
            json={"title": title},
        )
        assert response.status_code == 201
        task_ids.append(response.json()["id"])

    # Change the statuses of two tasks
    for task_id, status in [
        (task_ids[1], "in_progress"),
        (task_ids[2], "done"),
    ]:
        response = client.patch(
            f"/projects/{project_id}/tasks/{task_id}/status",
            headers=headers,
            json={"status": status},
        )
        assert response.status_code == 200

    # Request the summary
    response = client.get(
        f"/projects/{project_id}/tasks/summary",
        headers=headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total_tasks"] == 3
    assert data["todo"] == 1
    assert data["in_progress"] == 1
    assert data["done"] == 1




def test_filter_tasks_by_priority():
    from uuid import uuid4

    email = f"priority_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register a user
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Priority Test User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    # Log in
    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Priority Test Project",
            "description": "Testing priority filters",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Create tasks with different priorities
    for title, priority in [
        ("Low Priority Task", "low"),
        ("High Priority Task", "high"),
    ]:
        response = client.post(
            f"/projects/{project_id}/tasks",
            headers=headers,
            json={
                "title": title,
                "priority": priority,
            },
        )
        assert response.status_code == 201

    # Request only high-priority tasks
    response = client.get(
        f"/projects/{project_id}/tasks?priority=high",
        headers=headers,
    )

    assert response.status_code == 200

    tasks = response.json()
    assert len(tasks) == 1
    assert tasks[0]["title"] == "High Priority Task"
    assert tasks[0]["priority"] == "high"



def test_update_task():
    from uuid import uuid4

    email = f"update_{uuid4().hex[:8]}@example.com"
    password = "TestPassword123!"

    # Register a user
    register_response = client.post(
        "/auth/register",
        json={
            "name": "Update Test User",
            "email": email,
            "password": password,
        },
    )
    assert register_response.status_code == 201

    # Log in
    login_response = client.post(
        "/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Update Test Project",
            "description": "Testing task editing",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Create a task
    task_response = client.post(
        f"/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Original Task",
            "priority": "low",
        },
    )
    assert task_response.status_code == 201

    task_id = task_response.json()["id"]

    # Update the task
    update_response = client.put(
        f"/projects/{project_id}/tasks/{task_id}",
        headers=headers,
        json={
            "title": "Updated Task",
            "description": "Updated description",
            "priority": "high",
        },
    )

    assert update_response.status_code == 200

    updated_task = update_response.json()
    assert updated_task["title"] == "Updated Task"
    assert updated_task["description"] == "Updated description"
    assert updated_task["priority"] == "high"




def test_add_project_member():
    from uuid import uuid4

    unique_id = uuid4().hex[:8]
    password = "TestPassword123!"

    owner_email = f"owner_{unique_id}@example.com"
    member_email = f"member_{unique_id}@example.com"

    # Register the project owner and new member
    for name, email in [
        ("Project Owner", owner_email),
        ("Project Member", member_email),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
            },
        )
        assert response.status_code == 201

    # Log in as the owner
    login_response = client.post(
        "/auth/login",
        json={
            "email": owner_email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Find the member's user ID through the test database
    from models import UserDB

    db = TestSessionLocal()
    try:
        member = (
            db.query(UserDB)
            .filter(UserDB.email == member_email)
            .first()
        )
        assert member is not None
        member_id = member.id
    finally:
        db.close()

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Member Test Project",
            "description": "Testing member management",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Add the member to the project
    response = client.post(
        f"/projects/{project_id}/members",
        headers=headers,
        json={"user_id": member_id, "role": "member"},
    )

    assert response.status_code == 201
    assert response.json()["user_id"] == member_id
    assert response.json()["role"] == "member"



def test_cannot_add_same_member_twice():
    from uuid import uuid4
    from models import UserDB

    unique_id = uuid4().hex[:8]
    password = "TestPassword123!"

    owner_email = f"owner_{unique_id}@example.com"
    member_email = f"member_{unique_id}@example.com"

    # Register owner and member
    for name, email in [
        ("Duplicate Test Owner", owner_email),
        ("Duplicate Test Member", member_email),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
            },
        )
        assert response.status_code == 201

    # Log in as owner
    login_response = client.post(
        "/auth/login",
        json={
            "email": owner_email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Get the member's ID
    db = TestSessionLocal()
    try:
        member = (
            db.query(UserDB)
            .filter(UserDB.email == member_email)
            .first()
        )
        assert member is not None
        member_id = member.id
    finally:
        db.close()

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Duplicate Member Project",
            "description": "Testing duplicate prevention",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Add the member once
    first_response = client.post(
        f"/projects/{project_id}/members",
        headers=headers,
        json={"user_id": member_id, "role": "member"},
    )
    assert first_response.status_code == 201

    # Try to add the same member again
    second_response = client.post(
        f"/projects/{project_id}/members",
        headers=headers,
        json={"user_id": member_id, "role": "member"},
    )

    assert second_response.status_code == 409




def test_project_member_can_view_tasks():
    from uuid import uuid4
    from models import UserDB

    unique_id = uuid4().hex[:8]
    password = "TestPassword123!"

    owner_email = f"owner_{unique_id}@example.com"
    member_email = f"member_{unique_id}@example.com"

    # Register owner and member
    for name, email in [
        ("Access Test Owner", owner_email),
        ("Access Test Member", member_email),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
            },
        )
        assert response.status_code == 201

    # Log in as owner
    owner_login = client.post(
        "/auth/login",
        json={"email": owner_email, "password": password},
    )
    assert owner_login.status_code == 200

    owner_headers = {
        "Authorization": (
            f"Bearer {owner_login.json()['access_token']}"
        )
    }

    # Log in as member
    member_login = client.post(
        "/auth/login",
        json={"email": member_email, "password": password},
    )
    assert member_login.status_code == 200

    member_headers = {
        "Authorization": (
            f"Bearer {member_login.json()['access_token']}"
        )
    }

    # Find the member's user ID
    db = TestSessionLocal()
    try:
        member = (
            db.query(UserDB)
            .filter(UserDB.email == member_email)
            .first()
        )
        assert member is not None
        member_id = member.id
    finally:
        db.close()

    # Owner creates a project
    project_response = client.post(
        "/projects/",
        headers=owner_headers,
        json={
            "name": "Shared Project",
            "description": "Testing member task access",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Owner creates a task
    task_response = client.post(
        f"/projects/{project_id}/tasks",
        headers=owner_headers,
        json={"title": "Shared Task"},
    )
    assert task_response.status_code == 201

    # Owner adds the member
    member_response = client.post(
        f"/projects/{project_id}/members",
        headers=owner_headers,
        json={"user_id": member_id, "role": "member"},
    )
    assert member_response.status_code == 201

    # Member views the project's tasks
    response = client.get(
        f"/projects/{project_id}/tasks",
        headers=member_headers,
    )

    assert response.status_code == 200
    assert any(
        task["title"] == "Shared Task"
        for task in response.json()
    )




def test_non_member_cannot_view_project_tasks():
    from uuid import uuid4

    unique_id = uuid4().hex[:8]
    password = "TestPassword123!"

    owner_email = f"owner_{unique_id}@example.com"
    other_email = f"other_{unique_id}@example.com"

    # Register the owner and an unrelated user
    for name, email in [
        ("Privacy Test Owner", owner_email),
        ("Unrelated User", other_email),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
            },
        )
        assert response.status_code == 201

    # Log in as owner
    owner_login = client.post(
        "/auth/login",
        json={"email": owner_email, "password": password},
    )
    assert owner_login.status_code == 200

    owner_headers = {
        "Authorization": (
            f"Bearer {owner_login.json()['access_token']}"
        )
    }

    # Log in as unrelated user
    other_login = client.post(
        "/auth/login",
        json={"email": other_email, "password": password},
    )
    assert other_login.status_code == 200

    other_headers = {
        "Authorization": (
            f"Bearer {other_login.json()['access_token']}"
        )
    }

    # Owner creates a private project
    project_response = client.post(
        "/projects/",
        headers=owner_headers,
        json={
            "name": "Private Tasks Project",
            "description": "Testing task privacy",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Unrelated user tries to view its tasks
    response = client.get(
        f"/projects/{project_id}/tasks",
        headers=other_headers,
    )

    assert response.status_code == 403




def test_assign_task_to_project_member():
    from uuid import uuid4
    from models import UserDB

    unique_id = uuid4().hex[:8]
    password = "TestPassword123!"

    owner_email = f"owner_{unique_id}@example.com"
    member_email = f"member_{unique_id}@example.com"

    # Register owner and member
    for name, email in [
        ("Assignment Owner", owner_email),
        ("Assignment Member", member_email),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
            },
        )
        assert response.status_code == 201

    # Log in as owner
    login_response = client.post(
        "/auth/login",
        json={"email": owner_email, "password": password},
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Get the member's user ID
    db = TestSessionLocal()
    try:
        member = (
            db.query(UserDB)
            .filter(UserDB.email == member_email)
            .first()
        )
        assert member is not None
        member_id = member.id
    finally:
        db.close()

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Assignment Test Project",
            "description": "Testing task assignment",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Add the member to the project
    member_response = client.post(
        f"/projects/{project_id}/members",
        headers=headers,
        json={"user_id": member_id, "role": "member"},
    )
    assert member_response.status_code == 201

    # Create a task assigned to that member
    task_response = client.post(
        f"/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Member's Task",
            "assigned_to": member_id,
        },
    )

    assert task_response.status_code == 201
    assert task_response.json()["assigned_to"] == member_id



def test_cannot_assign_task_to_non_member():
    from uuid import uuid4
    from models import UserDB

    unique_id = uuid4().hex[:8]
    password = "TestPassword123!"

    owner_email = f"owner_{unique_id}@example.com"
    other_email = f"other_{unique_id}@example.com"

    # Register owner and unrelated user
    for name, email in [
        ("Assignment Owner", owner_email),
        ("Unrelated User", other_email),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
            },
        )
        assert response.status_code == 201

    # Log in as owner
    login_response = client.post(
        "/auth/login",
        json={"email": owner_email, "password": password},
    )
    assert login_response.status_code == 200

    headers = {
        "Authorization": (
            f"Bearer {login_response.json()['access_token']}"
        )
    }

    # Get the unrelated user's ID
    db = TestSessionLocal()
    try:
        other_user = (
            db.query(UserDB)
            .filter(UserDB.email == other_email)
            .first()
        )
        assert other_user is not None
        other_user_id = other_user.id
    finally:
        db.close()

    # Create a project
    project_response = client.post(
        "/projects/",
        headers=headers,
        json={
            "name": "Invalid Assignment Project",
            "description": "Testing assignment validation",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    # Try assigning a task to a non-member
    response = client.post(
        f"/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": "Invalid Assignment Task",
            "assigned_to": other_user_id,
        },
    )

    assert response.status_code == 400



def test_remove_member_loses_task_access():
    from uuid import uuid4
    from models import UserDB

    unique_id = uuid4().hex[:8]
    password = "TestPassword123!"

    owner_email = f"owner_{unique_id}@example.com"
    member_email = f"member_{unique_id}@example.com"

    # Register owner and member
    for name, email in [
        ("Removal Test Owner", owner_email),
        ("Removal Test Member", member_email),
    ]:
        response = client.post(
            "/auth/register",
            json={
                "name": name,
                "email": email,
                "password": password,
            },
        )
        assert response.status_code == 201

    # Log in as owner
    owner_login = client.post(
        "/auth/login",
        json={"email": owner_email, "password": password},
    )
    assert owner_login.status_code == 200

    owner_headers = {
        "Authorization": (
            f"Bearer {owner_login.json()['access_token']}"
        )
    }

    # Log in as member
    member_login = client.post(
        "/auth/login",
        json={"email": member_email, "password": password},
    )
    assert member_login.status_code == 200

    member_headers = {
        "Authorization": (
            f"Bearer {member_login.json()['access_token']}"
        )
    }

    # Find the member's ID
    db = TestSessionLocal()
    try:
        member = (
            db.query(UserDB)
            .filter(UserDB.email == member_email)
            .first()
        )
        assert member is not None
        member_id = member.id
    finally:
        db.close()

    # Create project and task
    project_response = client.post(
        "/projects/",
        headers=owner_headers,
        json={
            "name": "Member Removal Project",
            "description": "Testing member removal",
        },
    )
    assert project_response.status_code == 201

    project_id = project_response.json()["id"]

    task_response = client.post(
        f"/projects/{project_id}/tasks",
        headers=owner_headers,
        json={"title": "Private Project Task"},
    )
    assert task_response.status_code == 201

    # Add the member
    add_response = client.post(
        f"/projects/{project_id}/members",
        headers=owner_headers,
        json={"user_id": member_id, "role": "member"},
    )
    assert add_response.status_code == 201

    # Confirm member can access tasks
    before_removal = client.get(
        f"/projects/{project_id}/tasks",
        headers=member_headers,
    )
    assert before_removal.status_code == 200

    # Owner removes the member
    remove_response = client.delete(
        f"/projects/{project_id}/members/{member_id}",
        headers=owner_headers,
    )
    assert remove_response.status_code == 200

    # Confirm access is denied after removal
    after_removal = client.get(
        f"/projects/{project_id}/tasks",
        headers=member_headers,
    )
    assert after_removal.status_code == 403