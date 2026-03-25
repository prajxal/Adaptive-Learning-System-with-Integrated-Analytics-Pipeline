# Backend Codemap

## Entry Point

`backend/main.py` — Creates the FastAPI app, registers CORS, mounts all routers, imports all models for table creation.

## API Routes

### Auth — `backend/routers/auth.py` (prefix: `/auth`)
- `POST /auth/signup` — email/password signup, returns JWT
- `POST /auth/login` — email/password login, returns JWT
- `GET  /auth/me` — returns current user (Clerk auth)
- `POST /auth/google/exchange` — Supabase Google OAuth token exchange

### Users — `backend/routers/users.py` (prefix: `/users`)
- `GET  /users/me` — user details (id, email, elo, statuses)
- `GET  /users/me/profile` — completed courses, top skills
- `GET  /users/me/skills` — all skill profiles with progress per roadmap
- `POST /users/me/skills/rebuild` — calls `synthesize_all_skills_for_user()`
- `GET  /users/me/github-analysis` — GitHub language weights + top skills

### Courses — `backend/routers/courses.py` (prefix: `/courses`)
- `GET  /courses` — list courses (optional `roadmap_id`), calls `get_recommended_start_courses()`
- `GET  /courses/{course_id}` — single course detail
- `GET  /courses/{course_id}/roadmap` — prerequisite courses

### Resources — `backend/routers/resources.py` (prefix: `/courses`)
- `GET  /courses/{course_id}/resources` — ranked resources by adaptive score

### Learning Path — `backend/routers/learning_path.py` (prefix: `/learning-path`)
- `GET  /learning-path/{course_id}` — prerequisite chain + ELO-based status per node

### Recommend — `backend/routers/recommend.py` (prefix: `/recommend`)
- `GET  /recommend/recommend` — next courses in current roadmap + suggested new roadmaps

### Events — `backend/routers/events.py` (prefix: `/events`)
- `POST /events` — logs events; updates trust_score on `course_completed` / `quiz_failed`

### Progress — `backend/routers/progress.py` (prefix: `/progress`)
- `GET  /progress/roadmap/{roadmap_id}` — per-course completion map
- `GET  /progress/{roadmap_id}` — aggregate progress %, trust_score, proficiency

### Roadmaps — `backend/routers/roadmaps.py` (prefix: `/roadmaps`)
- `GET  /roadmaps` — list distinct roadmap_ids with topic counts

### Quiz — `backend/routers/quiz.py` (prefix: `/quiz`)
- `GET  /quiz/{skill_id}` — fetch or generate quiz via Gemini
- `POST /quiz/{skill_id}/submit` — evaluate answers, update profile, emit events

### Skill Graph — `backend/routers/skill_graph.py` (prefix: `/skill-graph`)
- `GET  /skill-graph/{roadmap_id}/status` — unlock status for all skills in roadmap

### Skill Profile — `backend/routers/skill_profile.py` (prefix: `/skill-profile`)
- `GET  /skill-profile/{skill_id}` — get or create profile with cold-start init

### GitHub Auth — `backend/routers/github_auth.py` (prefix: `/github`)
- `GET  /github/connect` — initiate OAuth flow
- `GET  /github/callback` — exchange code, extract skills in background
- `GET  /github/status` — connection status
- `POST /github/sync` — re-sync GitHub data
- `DELETE /github/disconnect` — remove GitHub connection

### Resume — `backend/routers/resume.py` (prefix: `/resume`)
- `POST /resume/upload` — upload PDF, process in background
- `GET  /resume/status` — processing status

## Services

| Service | File | Key Functions |
|---------|------|---------------|
| Recommendation | `services/learning_priority_service.py` | `get_unlocked_courses()`, `compute_importance_score()`, `get_recommended_start_courses()` |
| Skill Graph | `services/skill_graph_service.py` | `is_skill_unlocked()`, `is_skill_completed()`, `get_roadmap_skill_status()` |
| Quiz Scoring | `services/quiz_service.py` | `evaluate_quiz_attempt()` |
| Quiz Generation | `services/quiz_generation_service.py` | `get_or_generate_quiz()` (calls Gemini) |
| Skill Synthesis | `services/skill_synthesizer.py` | `get_skill_profile()` |
| Skill Profiles | `services/skill_profile_service.py` | `get_or_create_skill_profile()`, `update_skill_profile_from_quiz()`, `initialize_skill_profile_from_cold_start()` |
| GitHub Extractor | `services/github_skill_extractor.py` | `extract_github_skills()`, `synthesize_all_skills_for_user()` |
| Resume Parser | `services/resume_parser.py` | `ingest_resume()` |
| GitHub Service | `services/github_service.py` | GitHub API helpers |
| Video Content | `services/video_content_service.py` | YouTube/video helpers |

## Core Modules

- `core/clerk_auth.py` — `get_current_user()` dependency (Clerk JWT validation)
- `core/security.py` — `create_access_token()`, `hash_password()`, `verify_password()`
- `core/rate_limit.py` — `RateLimiter` class
- `db/database.py` — SQLAlchemy engine, `SessionLocal`, `Base`, `get_db()`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/extract_roadmaps.py` | Ingests roadmap.sh JSON into `courses` + `course_prerequisites` |
| `scripts/generate_skill_graph.py` | Generates `skill_edges` for a roadmap |
| `scripts/extract_roadmap_resources.py` | Extracts resources for roadmap courses |
| `scripts/seed_course_resources.py` | Seeds `course_resources` table |
| `scripts/compute_difficulty.py` | Computes difficulty levels |
