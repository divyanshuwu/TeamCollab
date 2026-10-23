import os

from fastapi import FastAPI
from routers.auth import router as auth_router
from routers.members import router as members_router
from routers.tasks import router as tasks_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,https://team-collab-theta.vercel.app",
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=[
        "Retry-After",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset-After",
    ],
)

app.include_router(auth_router)

from routers.projects import router as projects_router

app.include_router(projects_router)

app.include_router(members_router)

app.include_router(tasks_router)



@app.get("/")
def home():
    return {"message": "Welcome to TeamCollab API"}
