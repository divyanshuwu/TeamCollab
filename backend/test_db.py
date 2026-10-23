from database import SessionLocal


def test_database_session_can_be_created():
    db = SessionLocal()
    try:
        assert db.is_active
    finally:
        db.close()
