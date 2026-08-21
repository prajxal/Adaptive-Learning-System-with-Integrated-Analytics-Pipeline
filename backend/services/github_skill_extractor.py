import httpx
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

SKILL_LANGUAGE_MAP = {
    "Python": "python-developer",
    "JavaScript": "javascript",
    "TypeScript": "typescript",
    "Go": "golang",
    "Rust": "rust",
    "Java": "java",
    "C++": "cpp",
    "CSS": "css",
    "HTML": "html-css"
}


def compute_skill_weights(
    language_bytes: dict[str, int],
    language_commits: dict[str, int],
) -> list[dict]:
    """Pure function: compute combined skill weights from raw GitHub language data.

    This is the canonical weighting formula used by the production pipeline.
    Importing this function (rather than copying it) ensures the experiment always
    tests the exact same logic that runs in production.

    Args:
        language_bytes: Mapping of language name → total byte count across repos.
        language_commits: Mapping of language name → total commit count across repos.

    Returns:
        List of result dicts sorted by combined_weight descending::

            [{"roadmap_skill": str, "language": str,
              "combined_weight": float, "confidence": float}, ...]

        Only languages in SKILL_LANGUAGE_MAP with combined_weight > 0 are included.
    """
    total_bytes = sum(language_bytes.values()) or 1
    total_commits = sum(language_commits.values()) or 1

    results = []
    for lang, roadmap_skill in SKILL_LANGUAGE_MAP.items():
        b_count = language_bytes.get(lang, 0)
        c_count = language_commits.get(lang, 0)

        byte_weight = b_count / total_bytes
        commit_weight = c_count / total_commits
        combined_weight = (byte_weight * 0.6) + (commit_weight * 0.4)

        if combined_weight > 0:
            confidence = min(1.0, combined_weight * 2)
            results.append({
                "roadmap_skill": roadmap_skill,
                "language": lang,
                "combined_weight": round(combined_weight, 6),
                "confidence": round(confidence, 6),
            })

    return sorted(results, key=lambda x: x["combined_weight"], reverse=True)


def synthesize_all_skills_for_user(user_id: str, db) -> None:
    # Lazy imports: these modules require DATABASE_URL at import time.
    # Keeping them here lets this module be imported in experiment scripts
    # that run without a database connection.
    from models.skill_weight import SkillWeight  # noqa: PLC0415
    from services.skill_synthesizer import synthesize_skill_profile  # noqa: PLC0415

    skills = db.query(SkillWeight.skill_name).filter(SkillWeight.user_id == user_id).distinct().all()
    for (skill_name,) in skills:
        try:
            synthesize_skill_profile(user_id, skill_name, db)
        except Exception as e:
            logger.error(f"Error synthesizing skill {skill_name}: {e}", exc_info=True)


async def extract_github_skills(user_id: str, access_token: str) -> None:
    # Lazy imports: same reason as synthesize_all_skills_for_user above.
    from models.user import User  # noqa: PLC0415
    from models.skill_weight import SkillWeight  # noqa: PLC0415
    from db.database import SessionLocal  # noqa: PLC0415

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.github_status != "connected":
            return

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }

        language_bytes: dict[str, int] = {}
        language_commits: dict[str, int] = {}

        async with httpx.AsyncClient() as client:
            repos_url = "https://api.github.com/user/repos"
            repos = []
            page = 1
            while True:
                resp = await client.get(f"{repos_url}?per_page=100&page={page}", headers=headers)
                if resp.status_code != 200:
                    break

                data = resp.json()
                if not data:
                    break

                for r in data:
                    if r.get("fork") or r.get("archived"):
                        continue
                    repos.append(r)

                page += 1

            for repo in repos:
                repo_full_name = repo["full_name"]

                lang_resp = await client.get(
                    f"https://api.github.com/repos/{repo_full_name}/languages",
                    headers=headers,
                )
                if lang_resp.status_code == 200:
                    for lang, bytes_count in lang_resp.json().items():
                        language_bytes[lang] = language_bytes.get(lang, 0) + bytes_count

                commits_resp = await client.get(
                    f"https://api.github.com/repos/{repo_full_name}/commits?author={user.github_username}",
                    headers=headers,
                )
                if commits_resp.status_code == 200:
                    commits = commits_resp.json()
                    commit_count = len(commits) if isinstance(commits, list) else 0

                    primary_lang = repo.get("language")
                    if primary_lang:
                        language_commits[primary_lang] = language_commits.get(primary_lang, 0) + commit_count

            skill_entries = compute_skill_weights(language_bytes, language_commits)

            for entry in skill_entries:
                sw = db.query(SkillWeight).filter_by(
                    user_id=user_id,
                    skill_name=entry["roadmap_skill"],
                    source="github",
                ).first()

                if sw:
                    sw.weight = entry["combined_weight"]
                    sw.confidence = entry["confidence"]
                else:
                    db.add(SkillWeight(
                        user_id=user_id,
                        skill_name=entry["roadmap_skill"],
                        weight=entry["combined_weight"],
                        confidence=entry["confidence"],
                        source="github",
                    ))

            db.commit()

            synthesize_all_skills_for_user(user_id, db)

            user.github_sync_status = "completed"
            user.last_github_sync = datetime.utcnow()
            db.commit()

    except Exception as e:
        logger.error(f"Error in extract_github_skills: {e}", exc_info=True)
        try:
            db.rollback()
            if 'user' in locals() and user:
                user.github_sync_status = "failed"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
