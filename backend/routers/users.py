import time

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, distinct

from db.database import get_db
from models.skill_profile import SkillProfile
from models.course import Course
from models.event import Event
from models.user import User
from models.user_skill import UserSkill
from core.clerk_auth import get_current_user
from services.github_skill_extractor import synthesize_all_skills_for_user

router = APIRouter()

@router.get("/me")
def get_user_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "clerk_user_id": current_user.clerk_user_id,
        "email": current_user.email,
        "total_xp": getattr(current_user, "total_xp", None) or 0,
        "current_level": getattr(current_user, "current_level", None) or 1,
        "resume_status": current_user.resume_status,
        "github_sync_status": current_user.github_sync_status,
        "onboarding_completed": bool(getattr(current_user, "onboarding_completed", False)),
    }


@router.post("/me/onboarding/complete")
def complete_onboarding(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.onboarding_completed = True
    db.commit()
    return {"status": "ok"}

@router.get("/me/profile")
def get_user_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    
    # Get total completed courses
    completed_courses = db.query(func.count(distinct(Event.course_id))) \
        .filter(
            Event.user_id == user_id,
            Event.event_type == "course_completed"
        ).scalar() or 0

    # Get top 3 skills
    profiles = db.query(SkillProfile).filter(SkillProfile.user_id == user_id).all()
    skill_list = []
    
    if profiles:
        roadmap_ids = list(set(p.roadmap_id for p in profiles))
        for roadmap_id in roadmap_ids:
            roadmap_profiles = [p for p in profiles if p.roadmap_id == roadmap_id]
            avg_confidence = sum(p.confidence for p in roadmap_profiles) / len(roadmap_profiles)
            skill_list.append({
                "roadmap_id": roadmap_id,
                "confidence": avg_confidence
            })
            
        skill_list.sort(key=lambda x: x["confidence"], reverse=True)
        top_skills = [s["roadmap_id"] for s in skill_list[:3]]
    else:
        top_skills = []

    return {
        "total_xp": getattr(current_user, "total_xp", None) or 0,
        "current_level": getattr(current_user, "current_level", None) or 1,
        "resume_status": current_user.resume_status,
        "github_sync_status": current_user.github_sync_status,
        "last_github_sync": current_user.last_github_sync,
        "completed_courses": completed_courses,
        "top_skills": top_skills
    }

@router.get("/me/skills")
def get_user_skills(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _t0 = time.perf_counter()
    user_id = str(current_user.id)
    # Query all synthesized skills for the user
    profiles = db.query(SkillProfile).filter(SkillProfile.user_id == user_id).all()

    print(f"[UsersRouter] Fetching skills for {user_id}: found {len(profiles)} profiles")

    if not profiles:
        return {
            "user_id": user_id,
            "skills": []
        }

    skill_list = []

    # Get distinct roadmaps from the user's profiles
    roadmap_ids = list(set(p.roadmap_id for p in profiles))

    # Batch: total courses per roadmap (1 query)
    total_rows = db.query(Course.roadmap_id, func.count(Course.id).label("total")) \
        .filter(Course.roadmap_id.in_(roadmap_ids)) \
        .group_by(Course.roadmap_id) \
        .all()
    totals: dict[str, int] = {row.roadmap_id: int(row.total) for row in total_rows}

    # Batch: completed courses per roadmap (1 query)
    completed_rows = db.query(Event.roadmap_id, func.count(distinct(Event.course_id)).label("completed")) \
        .filter(
            Event.user_id == user_id,
            Event.event_type == "course_completed",
            Event.roadmap_id.in_(roadmap_ids),
        ) \
        .group_by(Event.roadmap_id) \
        .all()
    completeds: dict[str, int] = {row.roadmap_id: int(row.completed) for row in completed_rows}

    # Batch: UserSkill xp and level per roadmap (skill_name = roadmap_id)
    user_skill_rows = (
        db.query(UserSkill.skill_name, UserSkill.xp, UserSkill.level)
        .filter(
            UserSkill.user_id == user_id,
            UserSkill.skill_name.in_(roadmap_ids),
        )
        .all()
    )
    user_skill_map: dict[str, tuple[int, int]] = {
        str(row.skill_name): (int(row.xp or 0), int(row.level or 1))
        for row in user_skill_rows
    }

    for roadmap_id in roadmap_ids:
        roadmap_profiles = [p for p in profiles if p.roadmap_id == roadmap_id]
        avg_proficiency = sum(p.proficiency_level for p in roadmap_profiles) / len(roadmap_profiles)

        total_courses = totals.get(roadmap_id, 0)
        completed_courses = completeds.get(roadmap_id, 0)
        progress_percent = round((completed_courses / total_courses) * 100, 2) if total_courses > 0 else 0.0

        xp, level = user_skill_map.get(roadmap_id, (0, 1))

        skill_list.append({
            "roadmap_id": roadmap_id,
            "xp": xp,
            "level": level,
            "proficiency_level": float(avg_proficiency) if avg_proficiency else 0.0,
            "completed_courses": completed_courses,
            "total_courses": total_courses,
            "progress_percent": progress_percent,
            "last_updated": roadmap_profiles[0].updated_at if roadmap_profiles else None
        })

    print(f"[PERF] GET /users/me/skills took {(time.perf_counter() - _t0) * 1000:.0f}ms")
    return {
        "user_id": user_id,
        "skills": skill_list
    }

@router.post("/me/skills/rebuild")
def rebuild_skills(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user_id = str(current_user.id)
    synthesize_all_skills_for_user(user_id, db)
    return {"status": "success", "message": "Skills recalculated successfully"}


@router.get("/me/github-analysis")
def get_github_analysis(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns GitHub skill analysis data for the current user.
    Surfaces languages, commit weights, and top skills derived from
    the github-sourced SkillWeight rows — used to power frontend analytics.
    """
    _t0 = time.perf_counter()
    user_id = str(current_user.id)

    if current_user.github_status != "connected":
        print(f"[PERF] GET /users/me/github-analysis took {(time.perf_counter() - _t0) * 1000:.0f}ms (not connected)")
        return {
            "connected": False,
            "username": None,
            "sync_status": current_user.github_sync_status,
            "last_sync": None,
            "languages": [],
            "top_skills": [],
        }

    from models.skill_weight import SkillWeight

    github_weights = (
        db.query(SkillWeight)
        .filter(
            SkillWeight.user_id == user_id,
            SkillWeight.source == "github",
        )
        .all()
    )

    languages = [
        {
            "skill": sw.skill_name,
            "weight": round(sw.weight * 100, 1),       # as a percentage of total bytes
            "confidence": round(sw.confidence * 100, 1),
        }
        for sw in sorted(github_weights, key=lambda x: x.weight, reverse=True)
    ]

    # Top skills from SkillProfile (synthesized across all sources)
    profiles = db.query(SkillProfile).filter(SkillProfile.user_id == user_id).all()
    top_skills = sorted(
        [{"skill": p.roadmap_id, "proficiency": round(p.proficiency_level * 100, 1)} for p in profiles],
        key=lambda x: x["proficiency"],
        reverse=True,
    )[:5]

    print(f"[PERF] GET /users/me/github-analysis took {(time.perf_counter() - _t0) * 1000:.0f}ms")
    return {
        "connected": True,
        "username": current_user.github_username,
        "sync_status": current_user.github_sync_status,
        "last_sync": current_user.last_github_sync,
        "languages": languages,
        "top_skills": top_skills,
    }

