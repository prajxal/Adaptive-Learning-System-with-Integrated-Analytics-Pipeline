# Architecture Overview

LearnPathAI is a full-stack adaptive learning platform. Users connect GitHub and upload a resume; the backend synthesizes skill proficiency into an Elo-rated profile. A recommendation engine walks a prerequisite graph (sourced from roadmap.sh) and surfaces the highest-priority unlocked topic. Users study resources, take AI-generated quizzes, and their Elo updates to drive the next recommendation.

## System Diagram

```
Frontend (React + Vite + TypeScript)
  ├ ClerkProvider (auth)
  ├ PostHogProvider (analytics)
  ├ TokenSynchronizer (JWT sync)
  └ Pages → src/app/services/* → fetch()
                ↓
        FastAPI Backend (backend/main.py)
          ├ Routers (backend/routers/*)
          │   └ HTTP concerns only
          ├ Services (backend/services/*)
          │   ├ learning_priority_service  → recommendation engine
          │   ├ skill_graph_service        → graph traversal / unlock logic
          │   ├ quiz_service               → scoring + Elo updates
          │   ├ quiz_generation_service    → Gemini API quiz gen
          │   ├ skill_synthesizer          → merge GitHub + resume weights
          │   ├ github_skill_extractor     → GitHub API → SkillWeights
          │   ├ resume_parser              → PDF → SkillWeights
          │   └ skill_profile_service      → cold-start + profile CRUD
          └ Models (backend/models/*)
                ↓
          PostgreSQL (Supabase) via SQLAlchemy
```

## Key Data Flows

**Skill ingestion:** GitHub OAuth → `github_skill_extractor` → `SkillWeight` rows | Resume upload → `resume_parser` → `SkillWeight` rows → `skill_synthesizer` → `SkillProfile` rows.

**Recommendation:** `learning_priority_service.get_unlocked_courses()` filters by prerequisite completion → `compute_importance_score()` ranks by `(descendants*3)+(out_degree*2)+(10-depth)` → top course returned.

**Quiz loop:** `quiz_generation_service` calls Gemini API → stores `SkillQuiz` → user submits → `quiz_service.evaluate_quiz_attempt()` scores answers → calls `skill_profile_service.update_skill_profile_from_quiz()` → emits `course_completed` Event.

**Elo updates:** Occur inside `routers/learning_path.py` (`get_adaptive_skill_score`) and `routers/events.py` (trust_score adjustments on completion/failure).
