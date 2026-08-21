<!-- Generated: 2026-04-01 | Sprint: 5 (AI Mentor context injection) | /chat endpoint, MCP tools (get_user_profile, get_user_progress, get_next_course, get_roadmap_courses, get_skill_graph, build_user_context), function-calling loop -->

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
- `GET  /users/me` — user details: `id`, `email`, `total_xp`, `current_level`, `onboarding_completed` (Sprint 3), statuses
- `POST /users/me/onboarding/complete` — **NEW (Sprint 3):** mark onboarding as complete (sets `users.onboarding_completed = True`)
- `GET  /users/me/profile` — completed courses, top skills
- `GET  /users/me/skills` — all skill profiles with `xp`, `level` per roadmap (replaces `elo_rating`, `trust_score`)
- `POST /users/me/skills/rebuild` — calls `synthesize_all_skills_for_user()`
- `GET  /users/me/github-analysis` — GitHub language weights + top skills

### Courses — `backend/routers/courses.py` (prefix: `/courses`)
- `GET  /courses` — list courses with `required_level` (integer 1–6; replaces `difficulty_level`)
- `GET  /courses/{course_id}` — single course detail with `required_level`
- `GET  /courses/{course_id}/roadmap` — prerequisite courses

### Resources — `backend/routers/resources.py` (prefix: `/courses`)
- `GET  /courses/{course_id}/resources` — ranked resources by quality + is_primary (no longer ELO-distance)

### Learning Path — `backend/routers/learning_path.py` (prefix: `/learning-path`)
- `GET  /learning-path/{course_id}` — prerequisite chain + level-based status per node
- **`get_completed_course_ids(user_id, db)`** — returns `set[str]`; imported by `recommend.py`
- **Removed:** `get_adaptive_skill_score()`, `get_user_elo()` (level-based filtering now in `recommend.py`)

### Recommend — `backend/routers/recommend.py` (prefix: `/recommend`)
- `GET  /recommend/recommend?current_roadmap_id=X` — next courses + suggested new roadmaps
- **Returns:** `user_xp`, `user_level` (replaces `user_elo`)
- **Filtering:** `required_level ≤ user_level + 1` (replaces ELO-band logic)
- **Performance:** 4 queries total (completed_ids, courses, prereqs, skill profiles). Was 5,086 queries; now 4. Latency: ~400ms.

### Events — `backend/routers/events.py` (prefix: `/events`)
- `POST /events` — logs events; accepts `event_type: Literal["course_completed", "course_skipped", "quiz_started", "quiz_failed", "resource_viewed", "resource_completed"]`; calls `award_xp_for_completion()` on `course_completed` (replaces ELO updates)
- `DELETE /events/skip/{course_id}` — reverses a skip

### Progress — `backend/routers/progress.py` (prefix: `/progress`)
- `GET  /progress/roadmap/{roadmap_id}` — per-course completion map
- `GET  /progress/{roadmap_id}` — aggregate progress %, `xp`, `level` per roadmap (replaces `trust_score`)

### Roadmaps — `backend/routers/roadmaps.py` (prefix: `/roadmaps`)
- `GET  /roadmaps` — list distinct roadmap_ids with topic counts

### Quiz — `backend/routers/quiz.py` (prefix: `/quiz`)
- `GET  /quiz/{skill_id}` — fetch or generate quiz via Gemini; strips `correct_answer` + `explanation` from questions (prevents answer leakage)
- `POST /quiz/{skill_id}/submit` — evaluate answers, call `award_xp_for_quiz()`, emit events; **RETURNS:** `xp_awarded` (int), `total_xp` (int), `current_level` (int 1–6), `leveled_up` (bool)

### Skill Graph — `backend/routers/skill_graph.py` (prefix: `/skill-graph`)
- `GET  /skill-graph/{roadmap_id}/dynamic-status` — 5-state course status map. Each `DynamicCourseNode` includes `prerequisites: [{id, title, completed}]`
- `GET  /skill-graph/{roadmap_id}/status` — (**DEPRECATED**: Sunset 2026-06-01; use `/dynamic-status` instead)

### Skill Profile — `backend/routers/skill_profile.py` (prefix: `/skill-profile`)
- `GET  /skill-profile/{skill_id}` — get or create profile with cold-start init

### Chat (AI Mentor) — `backend/routers/chat.py` (prefix: `/chat`) **NEW (Sprint 5)**
- `POST /chat` — Gemini function-calling loop; accepts `{message: string}` (Clerk auth required); **pre-loads `build_user_context(user_id)` once** → injects into system prompt → runs max 5 tool-call rounds (60s timeout); returns `ChatResponse{reply: string}`
  - **Context Pre-Loading:** Before loop, calls `build_user_context(user_id)` (single DB session); queries User, top 5 UserSkills, most recent Event (active roadmap), completed count, next recommendation; returns plain-text block injected into dynamic system prompt. Fail-open: if context fails, uses base system prompt
  - **Gemini Model:** `gemini-3-flash-preview` (configurable via `GEMINI_CHAT_MODEL` env var); fallback chain: primary → fallback (2x retries on 503/timeout)
  - **Tools:** Declares 5 MCP tools in every request; model calls them, backend executes via `TOOL_REGISTRY`, feeds results back
  - **Security:** Router always overrides tool `user_id` args with authenticated user's ID (prevents LLM from querying other users)
  - **System Prompt:** Base prompt + live learner context; instructs Gemini to use tools to fetch real data before answering

### GitHub Auth — `backend/routers/github_auth.py` (prefix: `/github`)
- `GET  /github/connect` — initiate OAuth flow
- `GET  /github/callback` — exchange code, extract skills in background
- `GET  /github/status` — connection status `{ connected, username, sync_status }`
- `POST /github/sync` — re-sync GitHub data
- `DELETE /github/disconnect` — remove GitHub connection

### Resume — `backend/routers/resume.py` (prefix: `/resume`)
- `POST /resume/upload` — upload PDF, process in background
- `GET  /resume/status` — processing status

## Services

| Service | File | Key Functions |
|---------|------|---------------|
| **MCP Tools** | **`mcp_server/tools.py`** | **`get_user_profile(user_id)`**, **`get_user_progress(user_id)`**, **`get_next_course(user_id, roadmap_id)`**, **`get_roadmap_courses(roadmap_id)`**, **`get_skill_graph(roadmap_id, user_id?)`**, **`build_user_context(user_id)` (NEW)** — 5 tools called by Gemini function-calling loop via `TOOL_REGISTRY`; `build_user_context()` queries User + top 5 UserSkills + most recent Event (active roadmap) + completed course count + next recommendation; returns plain-text `## Learner Context` block injected into system prompt before loop |
| **MCP Registry** | **`mcp_server/registry.py`** | **`TOOL_DECLARATIONS`** (JSON schema), **`USER_ID_TOOLS`** (frozenset), **`TOOL_REGISTRY`** (dispatch table) |
| **XP / Level** | **`services/xp_level_service.py`** | **`award_xp_for_completion(user_id, course_id, roadmap_id, db)`**, **`award_xp_for_quiz(user_id, score, course_id, roadmap_id, db)`** (now validates score 0–1, returns `(xp, level_up)`), `compute_level_from_xp()`, `compute_xp_for_course(depth)`, `get_user_global_xp()`, `get_user_level()` |
| **Course Level** | **`services/course_level_service.py`** | **`compute_required_level(topological_depth)`** — maps depth 0–5 → level 1–6 |
| Dynamic Roadmap | `services/dynamic_roadmap_service.py` | `compute_dynamic_roadmap(user_id, roadmap_id, db)` returns courses with `prerequisites` field |
| Recommendation | `services/learning_priority_service.py` | `get_unlocked_courses()`, `compute_importance_score()`, `get_recommended_start_courses()` |
| Skill Graph | `services/skill_graph_service.py` | `is_skill_unlocked()`, `is_skill_completed()`, `get_roadmap_skill_status()` |
| Quiz Scoring | `services/quiz_service.py` | `evaluate_quiz_attempt()` — no longer calls Elo functions |
| Quiz Generation | `services/quiz_generation_service.py` | `get_or_generate_quiz()` (calls Gemini) |
| Skill Synthesis | `services/skill_synthesizer.py` | `get_skill_profile()` |
| Skill Profiles | `services/skill_profile_service.py` | `get_or_create_skill_profile()`, `update_skill_profile_from_quiz()`, `initialize_skill_profile_from_cold_start()` |
| GitHub Extractor | `services/github_skill_extractor.py` | `extract_github_skills()`, `synthesize_all_skills_for_user()` |
| Resume Parser | `services/resume_parser.py` | `ingest_resume()` |
| GitHub Service | `services/github_service.py` | GitHub API helpers |
| Video Content | `services/video_content_service.py` | YouTube/video helpers |

## Performance Instrumentation

Dashboard endpoints emit `[PERF] GET /path took Xms` to stdout. Instrumented: `/users/me/skills`, `/users/me/github-analysis`, `/roadmaps`, `/progress/all`, `/recommend/recommend`, `/courses`.

## Core Modules

- `core/clerk_auth.py` — `get_current_user()` dependency (Clerk JWT validation)
- `core/security.py` — `create_access_token()`, `hash_password()`, `verify_password()`
- `core/rate_limit.py` — `RateLimiter` class; **FIXED:** uses `X-Forwarded-For` last IP (was using first IP, spoofable on shared reverse proxies)
- `db/database.py` — SQLAlchemy engine, `SessionLocal`, `Base`, `get_db()`

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/extract_roadmaps.py` | Ingests roadmap.sh JSON into `courses` + `course_prerequisites` |
| `scripts/generate_skill_graph.py` | Generates `skill_edges` for a roadmap |
| `scripts/extract_roadmap_resources.py` | Extracts resources for roadmap courses |
| `scripts/seed_course_resources.py` | Seeds `course_resources` table |
| `scripts/compute_difficulty.py` | Computes `difficulty_level` (legacy; future: call `course_level_service` to populate `required_level`) |
| `scripts/migrate_elo_to_xp.py` | **NEW (Phase 2):** One-time backfill of ELO→XP for existing users; safe to run multiple times |
