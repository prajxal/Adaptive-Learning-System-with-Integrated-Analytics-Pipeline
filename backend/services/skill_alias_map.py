"""
Canonical alias map for resume skill detection.

Maps lowercase text aliases → canonical roadmap skill IDs.
Multiple aliases can map to the same skill ID.

This is the single source of truth for skill aliases used by the
resume extraction pipeline. To add new skills, extend RESUME_SKILL_MAP.
Aliases are matched with word-boundary regex, longest aliases first to
prevent substring collisions (e.g. "react" inside "react native").
"""

from __future__ import annotations

RESUME_SKILL_MAP: dict[str, str] = {
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
    "react native": "react-native",
    "react.js": "react",
    "reactjs": "react",
    "react": "react",
    "vue.js": "vue",
    "vuejs": "vue",
    "vue": "vue",
    "angularjs": "angular",
    "angular": "angular",
    "svelte": "frontend",
    "html/css": "html-css",
    "html": "html-css",
    "css": "html-css",
    "sass": "html-css",
    "tailwindcss": "frontend",
    "tailwind": "frontend",
    "next.js": "react",
    "nextjs": "react",
    "nuxt": "vue",
    # Backend
    "node.js": "nodejs",
    "nodejs": "nodejs",
    "node": "nodejs",
    "expressjs": "nodejs",
    "express": "nodejs",
    "django": "python",
    "flask": "python",
    "fastapi": "python",
    "spring boot": "java",
    "spring": "java",
    "laravel": "php",
    "ruby on rails": "ruby",
    "rails": "ruby",
    "asp.net": "csharp",
    "graphql": "backend",
    "restful": "backend",
    "rest": "backend",
    # DevOps / Cloud
    "docker": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "amazon web services": "aws",
    "aws": "aws",
    "google cloud": "gcp",
    "gcp": "gcp",
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
    "data science": "ai",
    "scikit-learn": "ai",
    "tensorflow": "ai",
    "pytorch": "ai",
    "pandas": "python",
    "numpy": "python",
    "nlp": "ai",
    "llm": "ai",
    "ml": "ai",
    # Mobile
    "android": "android",
    "ios": "ios",
    "flutter": "flutter",
    # Other
    "microservices": "backend",
    "websocket": "backend",
    "rabbitmq": "backend",
    "kafka": "backend",
    "grpc": "backend",
    "github": "backend",
    "git": "backend",
    "agile": "backend",
    "scrum": "backend",
    "solidity": "blockchain",
    "blockchain": "blockchain",
    "cybersecurity": "cyber-security",
    "security": "cyber-security",
    "devops": "devops",
    "frontend": "frontend",
    "backend": "backend",
    "full-stack": "fullstack",
    "full stack": "fullstack",
    "fullstack": "fullstack",
    "testing": "qa",
    "qa": "qa",
}

# Pre-sorted aliases (longest first) to prevent substring collisions.
# e.g. "react native" is matched before "react", "spring boot" before "spring".
SORTED_ALIASES: list[tuple[str, str]] = sorted(
    RESUME_SKILL_MAP.items(), key=lambda kv: len(kv[0]), reverse=True
)


def get_skill_id(alias: str) -> str | None:
    """Return the canonical skill ID for a given alias, or None if unknown."""
    return RESUME_SKILL_MAP.get(alias.lower().strip())
