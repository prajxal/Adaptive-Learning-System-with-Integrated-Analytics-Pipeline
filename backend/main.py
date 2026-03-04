from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers.events import router as events_router
from routers.recommend import router as recommend_router
from routers.users import router as users_router
from routers import auth
from routers import courses
from routers import courses
from routers import learning_path
from routers import courses
from routers import learning_path
from routers import roadmaps
from routers import progress
from routers import github_auth
from routers import resume
from routers import resources
from routers import skill_graph
from routers import quiz
from routers import skill_profile
from db.database import engine, Base

# Import all models to ensure metadata.create_all registers them
import models.course
import models.course_prerequisite
import models.course_resource
import models.event
import models.skill_profile
import models.skill_weight
import models.user
import models.user_skill

Base.metadata.create_all(bind=engine)

app = FastAPI(title="AI Learning Path Recommendation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommend_router, prefix="/recommend", tags=["recommend"])
app.include_router(events_router, prefix="/events", tags=["events"])
app.include_router(users_router, prefix="/users", tags=["users"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(courses.router, prefix="/courses", tags=["courses"])
app.include_router(
    learning_path.router,
    prefix="/learning-path",
    tags=["learning-path"]
)
app.include_router(roadmaps.router, prefix="/roadmaps", tags=["roadmaps"])
app.include_router(progress.router, prefix="/progress", tags=["progress"])
from routers.github_auth import router as github_router
app.include_router(github_router)
app.include_router(resume.router, prefix="/resume", tags=["resume"])
app.include_router(resources.router, prefix="/courses", tags=["resources"])
app.include_router(skill_graph.router, prefix="/skill-graph", tags=["skill-graph"])
app.include_router(quiz.router, prefix="/quiz", tags=["quiz"])
app.include_router(skill_profile.router, prefix="/skill-profile", tags=["skill-profile"])

@app.get("/")
def health_check():
    return {"status": "backend running"}
