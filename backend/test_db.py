from database import SessionLocal

db = SessionLocal()

print("Database session created successfully!")

db.close()

print("Database session closed!")