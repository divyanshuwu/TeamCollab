from database import SessionLocal
from models import ProjectDB

db = SessionLocal()

try:
    new_project = ProjectDB(
        name = "TeamCollab",
        description = "Project management and team collaboration platform"
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    print("Project created succesfully!")
    print("Project ID:", new_project.id)
    print("Project Name:", new_project.name)

except Exception as e:
    db.rollback()
    print("Error:", e)

finally:
    db.close()