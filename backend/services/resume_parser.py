import pdfplumber
import re
from sqlalchemy.orm import Session

from models.skill_weight import SkillWeight
from services.github_skill_extractor import synthesize_all_skills_for_user

# Maps resume text aliases → canonical roadmap skill IDs.
# Keys are lowercase; multiple aliases can map to the same skill ID.
RESUME_SKILL_MAP = {
    # Languages
    "python": "python",
    "javascript": "javascript",
    "typescript": "typescript",
    "java": "java",
    "golang": "golang",
    "go": "golang",
    "rust": "rust",
    "c++": "cpp",
    "cpp": "cpp",
    "c#": "csharp",
    "csharp": "csharp",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin",
    "scala": "scala",
    "r": "r",
    # Frontend
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "vue": "vue",
    "vuejs": "vue",
    "vue.js": "vue",
    "angular": "angular",
    "angularjs": "angular",
    "svelte": "frontend",
    "html": "html-css",
    "css": "html-css",
    "html/css": "html-css",
    "sass": "html-css",
    "tailwind": "frontend",
    "tailwindcss": "frontend",
    "next.js": "react",
    "nextjs": "react",
    "nuxt": "vue",
    # Backend
    "node": "nodejs",
    "node.js": "nodejs",
    "nodejs": "nodejs",
    "express": "nodejs",
    "expressjs": "nodejs",
    "django": "python",
    "flask": "python",
    "fastapi": "python",
    "spring": "java",
    "spring boot": "java",
    "laravel": "php",
    "rails": "ruby",
    "ruby on rails": "ruby",
    "asp.net": "csharp",
    "graphql": "backend",
    "rest": "backend",
    "restful": "backend",
    # DevOps / Cloud
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "azure": "azure",
    "terraform": "terraform",
    "ansible": "devops",
    "jenkins": "devops",
    "github actions": "devops",
    "ci/cd": "devops",
    "linux": "linux",
    "bash": "linux",
    "shell": "linux",
    "nginx": "devops",
    # Databases
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "mysql": "mysql",
    "mongodb": "mongodb",
    "redis": "redis",
    "elasticsearch": "backend",
    "sqlite": "backend",
    "cassandra": "backend",
    # AI / ML / Data
    "machine learning": "ai",
    "deep learning": "ai",
    "ml": "ai",
    "tensorflow": "ai",
    "pytorch": "ai",
    "scikit-learn": "ai",
    "pandas": "python",
    "numpy": "python",
    "data science": "ai",
    "nlp": "ai",
    "llm": "ai",
    # Mobile
    "android": "android",
    "ios": "ios",
    "react native": "react-native",
    "flutter": "flutter",
    # Other
    "git": "backend",
    "github": "backend",
    "agile": "backend",
    "scrum": "backend",
    "microservices": "backend",
    "kafka": "backend",
    "rabbitmq": "backend",
    "grpc": "backend",
    "websocket": "backend",
    "blockchain": "blockchain",
    "solidity": "blockchain",
    "cybersecurity": "cyber-security",
    "security": "cyber-security",
    "devops": "devops",
    "frontend": "frontend",
    "backend": "backend",
    "fullstack": "fullstack",
    "full stack": "fullstack",
    "full-stack": "fullstack",
    "qa": "qa",
    "testing": "qa",
}


def extract_text_from_pdf(file_path: str) -> str:
    print(f"[ResumeParser] Starting text extraction from {file_path}")
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""

    print(f"[ResumeParser] Resume parsed successfully. Extracted {len(text)} characters.")
    return text.lower()


def extract_skills_from_text(text: str) -> dict:
    print("[ResumeParser] Starting skill extraction using alias map...")
    skill_counts: dict[str, int] = {}

    for alias, skill_id in RESUME_SKILL_MAP.items():
        occurrences = len(re.findall(r"\b" + re.escape(alias) + r"\b", text))
        if occurrences > 0:
            skill_counts[skill_id] = skill_counts.get(skill_id, 0) + occurrences

    print(f"[ResumeParser] Skills extracted: {skill_counts}")
    return skill_counts


def ingest_resume(file_path: str, user_id: str, db: Session):
    print(f"[ResumeParser] Ingestion initiated for user {user_id}")
    text = extract_text_from_pdf(file_path)
    skill_scores = extract_skills_from_text(text)

    if not skill_scores:
        print("[ResumeParser] No recognizable skills found in resume.")
        return

    max_score = max(skill_scores.values())

    for skill_name, score in skill_scores.items():
        normalized_weight = score / max_score
        confidence = min(1.0, score / 5.0)

        existing = db.query(SkillWeight).filter(
            SkillWeight.user_id == user_id,
            SkillWeight.skill_name == skill_name,
            SkillWeight.source == "resume"
        ).first()

        if existing:
            existing.weight = normalized_weight
            existing.confidence = confidence
            print(f"[ResumeParser] Updated existing SkillWeight for {skill_name}")
        else:
            db.add(SkillWeight(
                user_id=user_id,
                skill_name=skill_name,
                weight=normalized_weight,
                confidence=confidence,
                source="resume"
            ))
            print(f"[ResumeParser] Inserted new SkillWeight for {skill_name}")

    db.commit()
    print("[ResumeParser] SkillWeights committed. Running synthesis...")

    try:
        synthesize_all_skills_for_user(user_id, db)
    except Exception as e:
        print(f"[ResumeParser] Non-fatal error during synthesis: {e}")

    print("[ResumeParser] Ingestion pipeline complete.")
