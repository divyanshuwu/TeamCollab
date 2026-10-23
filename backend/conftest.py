import os

# Keep the API test suite isolated from developer or production databases.
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET_KEY"] = "test-only-signing-key-with-at-least-32-bytes"
