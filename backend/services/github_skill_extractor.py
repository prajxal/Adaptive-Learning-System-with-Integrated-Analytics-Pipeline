import httpx
from sqlalchemy.orm import Session
from models.user import User
from models.skill_weight import SkillWeight
from db.database import SessionLocal
from services.skill_synthesizer import synthesize_skill_profile

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

def synthesize_all_skills_for_user(user_id: str, db: Session):
    skills = db.query(SkillWeight.skill_name).filter(SkillWeight.user_id == user_id).distinct().all()
    for (skill_name,) in skills:
        try:
            synthesize_skill_profile(user_id, skill_name, db)
        except Exception as e:
            print(f"[GithubSkillExtractor] Error synthesizing skill {skill_name}: {e}")

async def extract_github_skills(user_id: str, access_token: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.github_status != "connected":
            return

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        
        language_bytes = {}
        language_commits = {}

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
                
                lang_resp = await client.get(f"https://api.github.com/repos/{repo_full_name}/languages", headers=headers)
                if lang_resp.status_code == 200:
                    for lang, bytes_count in lang_resp.json().items():
                        language_bytes[lang] = language_bytes.get(lang, 0) + bytes_count
                
                commits_resp = await client.get(f"https://api.github.com/repos/{repo_full_name}/commits?author={user.github_username}", headers=headers)
                if commits_resp.status_code == 200:
                    commits = commits_resp.json()
                    commit_count = len(commits) if isinstance(commits, list) else 0
                    
                    primary_lang = repo.get("language")
                    if primary_lang:
                        language_commits[primary_lang] = language_commits.get(primary_lang, 0) + commit_count

            total_bytes = sum(language_bytes.values()) or 1
            total_commits = sum(language_commits.values()) or 1

            for lang, roadmap_skill in SKILL_LANGUAGE_MAP.items():
                b_count = language_bytes.get(lang, 0)
                c_count = language_commits.get(lang, 0)

                byte_weight = b_count / total_bytes
                commit_weight = c_count / total_commits

                combined_weight = (byte_weight * 0.6) + (commit_weight * 0.4)

                if combined_weight > 0:
                    confidence = min(1.0, combined_weight * 2)

                    sw = db.query(SkillWeight).filter_by(
                        user_id=user_id,
                        skill_name=roadmap_skill,
                        source="github"
                    ).first()

                    if sw:
                        sw.weight = combined_weight
                        sw.confidence = confidence
                    else:
                        db.add(SkillWeight(
                            user_id=user_id,
                            skill_name=roadmap_skill,
                            weight=combined_weight,
                            confidence=confidence,
                            source="github"
                        ))

            db.commit()

            synthesize_all_skills_for_user(user_id, db)

    except Exception as e:
        print(f"Error in extract_github_skills: {e}")
    finally:
        db.close()
