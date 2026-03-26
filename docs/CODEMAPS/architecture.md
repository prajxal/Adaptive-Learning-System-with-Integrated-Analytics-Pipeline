<!-- Generated: 2026-03-26 | Session: dynamic-roadmap + reason-metadata + bug-fixes -->

# Architecture Overview

LearnPathAI is a full-stack adaptive learning platform. Users connect GitHub and upload a resume; the backend synthesizes skill proficiency into an Elo-rated profile. A dynamic roadmap engine surfaces a 5-state course map (locked | unlocked | fast_tracked | skippable | completed) driven by confidence thresholds. Users study resources, take AI-generated quizzes, skip courses, and their Elo/confidence updates to drive the next recommendation.

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

**Dynamic roadmap status (new):** `compute_dynamic_roadmap()` fetches 4 data sets in parallel — (Q1) all courses for roadmap; (Q2) satisfied IDs (completed events + skipped events + quiz passes); (Q3) prerequisites; (Q4) skill profiles — then applies 5-state resolution engine:
1. **completed** — if course_id in satisfied_ids
2. **skippable** — if all prereqs satisfied AND confidence ≥ SKIP_CONFIDENCE_THRESHOLD (0.75 default)
3. **fast_tracked** — if all prereqs satisfied AND confidence ≥ FAST_TRACK_CONFIDENCE_THRESHOLD (0.50 default)
4. **unlocked** — if all prereqs satisfied
5. **locked** — otherwise
Each course includes a `reason` caption describing why it has that state (GitHub signal, resume signal, high confidence, locked prerequisites, etc.)

**Skip/unskip:** Frontend calls `skipCourse()` → validates confidence + prerequisite completion + no duplicate completion → `POST /events {event_type: course_skipped, course_id}` → emits Event. Unskip is `DELETE /events/skip/{course_id}`.

**Quiz loop:** `quiz_generation_service` calls Gemini API → stores `SkillQuiz` → user submits → `quiz_service.evaluate_quiz_attempt()` scores answers → calls `skill_profile_service.update_skill_profile_from_quiz()` → emits `course_completed` Event.

**Elo updates:** Occur inside `routers/learning_path.py` (`get_adaptive_skill_score`) and `routers/events.py` (trust_score adjustments on completion/failure).
