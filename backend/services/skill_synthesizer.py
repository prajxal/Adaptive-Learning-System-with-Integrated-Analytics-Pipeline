from sqlalchemy.orm import Session
from datetime import datetime

from models.skill_weight import SkillWeight
from models.skill_profile import SkillProfile

def synthesize_skill_profile(user_id: str, skill_id: str, db: Session) -> SkillProfile:

    weights = db.query(SkillWeight).filter(
        SkillWeight.user_id == user_id,
        SkillWeight.skill_name == skill_id
    ).all()
    
    print(f"[SkillSynth Debug] weights extracted count: {len(weights)} for user {user_id}, skill {skill_id}")

    if not weights:
        print(f"[SkillSynth Debug] No weights found, aborting synthesis early.")
        return None

    SOURCE_MULTIPLIERS = {
        "github": 1.0,
        "resume": 0.6,
        "quiz": 1.3,
        "engagement": 1.1
    }

    numerator = 0.0
    denominator = 0.0

    for w in weights:
        multiplier = SOURCE_MULTIPLIERS.get(w.source, 1.0)
        numerator += w.weight * w.confidence * multiplier
        denominator += w.confidence * multiplier

    if denominator == 0:
        return None

    synthesized_weight = numerator / denominator
    aggregated_confidence = min(1.0, denominator / len(weights))

    profile = db.query(SkillProfile).filter(
        SkillProfile.user_id == user_id,
        SkillProfile.skill_id == skill_id
    ).first()

    if not profile:
        from models.course import Course
        # Attempt to map skill_id back to a real course and extract roadmap_id
        course = db.query(Course).filter(Course.roadmap_id == skill_id).first()
        mapped_roadmap = course.roadmap_id if course else skill_id
        
        print(f"[SkillSynth Debug] Resolved missing profile mapping {skill_id} to roadmap {mapped_roadmap}")

        profile = SkillProfile(
            user_id=user_id,
            skill_id=skill_id,
            roadmap_id=mapped_roadmap
        )
        db.add(profile)
    else:
        print(f"[SkillSynth Debug] Profile found existing id={profile.id}")

    profile.proficiency_level = synthesized_weight
    profile.confidence = aggregated_confidence

    db.commit()
    db.refresh(profile)
    
    print(f"[SkillSynth] user={user_id} skill={skill_id} roadmap={profile.roadmap_id} weight={synthesized_weight}")

    return profile


def get_skill_profile(user_id: str, skill_id: str, db: Session) -> SkillProfile:
    return db.query(SkillProfile).filter(
        SkillProfile.user_id == user_id,
        SkillProfile.skill_id == skill_id
    ).first()
