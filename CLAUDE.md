# CLAUDE.md

This file provides guidance to Claude Code when working with the LearnPathAI repository.

---

## Repository Codemaps

Before scanning the repository, first read these AI-optimized architecture maps:

- `docs/CODEMAPS/architecture.md` — system overview, data flows, subsystem diagram
- `docs/CODEMAPS/backend.md` — all API routes, services, core modules, scripts
- `docs/CODEMAPS/frontend.md` — routes, components, API service layer, hooks
- `docs/CODEMAPS/data.md` — all database models, columns, relationships, migrations

Claude should use these maps to locate relevant files quickly and avoid unnecessary repository scanning.

---

## What This Project Is

**LearnPathAI** is an adaptive learning platform that solves "tutorial hell" by analyzing a developer's existing skills (via Resume PDF and GitHub profile) and generating a personalized, topology-aware learning curriculum.

The core loop:
1. User connects GitHub + uploads Resume → system infers skill proficiency
2. Backend synthesizes skills into an Elo-rated skill profile (starting at 1000)
3. Recommendation engine walks the roadmap.sh prerequisite graph and surfaces the highest-priority unlocked topic
4. User engages with resources → takes a quiz → Elo updates → next recommendation fires

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + TypeScript, React Router v7 |
| Styling | Tailwind CSS + shadcn/ui components |
| Backend | FastAPI (Python) |
| Database | PostgreSQL via SQLAlchemy ORM |
| Auth | Clerk (JWT-based, `clerk_user_id` maps to `users` table) |
| AI/Quiz | Google Gemini API |
| Analytics | PostHog (frontend) |
| Hosting | Vercel (frontend), Render (backend) |
| DB Host | Supabase PostgreSQL |

---

## Repository Layout

```
AI Learning Path Generator/
├── CLAUDE.md                  ← you are here
├── .claude/
│   ├── agents/                ← subagent definitions
│   ├── commands/              ← slash commands
│   ├── hooks/                 ← session lifecycle scripts + settings.json
│   ├── memory/                ← project-memory.json, learned-patterns.json, mistakes.json
│   ├── rules/                 ← always-follow guidelines
│   └── skills/                ← workflow skills (includes React Router 7, PostHog)
├── backend/
│   ├── core/                  ← auth (Clerk), rate limiting, security
│   ├── db/                    ← SQLAlchemy engine + session
│   ├── migrations/            ← Alembic migration versions
│   ├── models/                ← SQLAlchemy ORM models (see Database Schema below)
│   ├── routers/               ← FastAPI route handlers
│   ├── scripts/               ← one-off data scripts (roadmap ingestion, seeding, etc.)
│   ├── services/              ← business logic (quiz gen, Elo, skill synthesis, etc.)
│   ├── main.py                ← FastAPI app entrypoint
│   └── requirements.txt
├── src/
│   ├── app/
│   │   ├── components/        ← shared UI components (Navbar, Sidebar, RoadmapNode, etc.)
│   │   ├── pages/             ← route-level page components
│   │   ├── hooks/             ← React hooks (useProgress, useRecommendation)
│   │   └── services/          ← frontend API call wrappers
│   ├── components/dashboard/  ← dashboard-specific cards (GitHub, Skill, Snapshot)
│   ├── hooks/                 ← global hooks (useCourses, useRoadmaps, useUserSkills)
│   ├── services/              ← granular API modules (courseApi, roadmapApi, etc.)
│   ├── auth/                  ← PostHogIdentifier, TokenSynchronizer
│   └── lib/supabase.ts        ← Supabase client
├── scripts/                   ← root-level utility scripts (moved from root)
└── index.html
```

---

## Database Schema (Critical Reference)

**Never modify schema without creating an Alembic migration.**

| Model | File | Key Fields | Notes |
|---|---|---|---|
| `User` | `models/user.py` | `id`, `clerk_user_id`, `email`, `global_elo_rating` (default 1000.0) | Central entity |
| `UserSkill` | `models/user_skill.py` | `skill_name`, `proficiency_level`, `elo_rating`, `trust_score` | Per-skill rating |
| `Course` | `models/course.py` | `id` = `{roadmap_id}:{node_id}`, `difficulty_level` | Composite PK |
| `CoursePrerequisite` | `models/course_prerequisite.py` | `course_id`, `prerequisite_id` | Dependency graph |
| `CourseResource` | `models/course_resource.py` | `course_id`, `resource_type`, `url` | Videos/articles |
| `SkillWeight` | `models/skill_weight.py` | Intermediate ingestion scoring | Do not confuse with UserSkill |
| `SkillProfile` | `models/skill_profile.py` | Synthesized output of ingestion | Built from SkillWeights |
| `QuizAttempt` | `models/quiz_attempt.py` | Quiz history | Drives confidence updates |
| `Event` | `models/event.py` | `event_type`, `payload` (JSON) | Analytics event log |

**Elo bounds:** minimum 800, maximum 2000.
**Course difficulty formula:** `800 + (topological_depth * 100)`

---

## Architecture Rules

These are hard constraints. Do not violate them.

**Frontend:**
- Frontend NEVER accesses the database directly — all data goes through FastAPI
- Frontend uses Clerk JWT tokens; `TokenSynchronizer` handles refresh
- API base URL comes from environment variable — never hardcode it
- PostHog tracking calls belong in page components, not in API service files

**Backend:**
- All DB access goes through SQLAlchemy ORM — never raw SQL strings
- Schema changes require an Alembic migration file — never `ALTER TABLE` directly
- Clerk auth validation happens in `core/clerk_auth.py` — do not duplicate this logic
- Rate limiting is in `core/rate_limit.py` — note: Render's shared reverse proxy means IP-based rate limiting needs the forwarded IP header, not `request.client.host`
- Router files handle HTTP concerns only — business logic lives in `services/`

**Skill Graph:**
- `skill_edges` dependencies come from roadmap JSON source data, NOT sorted by `Course.id`
- Prerequisite direction: `course_id` = the dependent (what needs unlocking), `prerequisite_id` = what must be done first
- BFS traversal collapses non-topic nodes when building the prerequisite graph

---

## Running the Project

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Required environment variables (`.env` in `backend/`):
```
DATABASE_URL=postgresql://...
CLERK_SECRET_KEY=sk_...
GEMINI_API_KEY=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

### Frontend

```bash
npm install
npm run dev
```

Required environment variables (`.env` at root):
```
VITE_API_URL=http://localhost:8000
VITE_CLERK_PUBLISHABLE_KEY=pk_...
VITE_SUPABASE_URL=...
VITE_SUPABASE_ANON_KEY=...
VITE_POSTHOG_KEY=...
```

### Database Migrations

```bash
cd backend
alembic upgrade head       # apply migrations
alembic revision --autogenerate -m "description"  # create new migration
```

---

## Key Services — What They Do

| Service | File | Responsibility |
|---|---|---|
| Skill Synthesis | `services/skill_synthesizer.py` | Merges GitHub + Resume SkillWeights into unified SkillProfile |
| Quiz Generation | `services/quiz_generation_service.py` | Calls Gemini to generate questions for a given course |
| Quiz Scoring | `services/quiz_service.py` | Scores answers, updates Elo, updates confidence |
| Learning Priority | `services/learning_priority_service.py` | `get_unlocked_courses()` + importance score ranking |
| Skill Graph | `services/skill_graph_service.py` | Graph traversal, descendant counts, topological depth |
| GitHub Extractor | `services/github_skill_extractor.py` | Maps language byte-counts + commits → SkillWeights |
| Resume Parser | `services/resume_parser.py` | pdfplumber text extraction → regex skill matching |

---

## Recommendation Algorithm (Do Not Accidentally Break)

Located in `services/learning_priority_service.py`.

```
importance_score = (descendants_count * 3) + (out_degree * 2) + (10 - graph_depth)
```

- `get_unlocked_courses()` returns courses where ALL prerequisites are completed and the course itself is not completed
- Top-scoring course = `recommended`, next two = `alternatives`
- **Known limitation:** Does not yet incorporate Elo-based difficulty matching — this is intentional for now

---

## Elo System (Do Not Accidentally Break)

- Standard logistic formula: `E = 1 / (1 + 10^((course_elo - user_elo) / 400))`
- Actual score: `1.0` if quiz ≥ 80%, `0.5` if ≥ 50%, `0.0` if < 50%
- K-factor: 32
- Updates fire in `update_skill_profile_from_quiz` after quiz completion

---

## Confidence Score System

- Before quizzes: `max(github_confidence, resume_confidence)`
- After quiz: `new_quiz_confidence = min(1.0, old_quiz_confidence + 0.2)` — progressively increases
- Final proficiency uses a weighted EMA combining history, new quiz result, and old confidence
- High confidence = harder to shift proficiency (trust anchors the rating)

---

## Known Issues / Watch Out For

| Issue | Location | Status |
|---|---|---|
| Rate limiter uses wrong IP on Render | `core/rate_limit.py` | Needs forwarded IP header fix |
| GitHub OAuth env vars differ per environment | `routers/github_auth.py` | Must set on Render dashboard AND GitHub OAuth App |
| Skill edges must come from JSON source, not `Course.id` sort | `scripts/generate_skill_graph.py` | Fixed; do not reintroduce |
| Confidence score can overflow 100% | `services/quiz_service.py` | Fixed; `min(1.0, ...)` guard must stay |

---

## Agent Delegation Guide

When delegating to subagents, use these as the routing rules:

- **planner** → before any feature work; produces a step-by-step plan
- **backend-engineer** → FastAPI routers, SQLAlchemy models, Alembic migrations, services
- **frontend-engineer** → React components, Tailwind, Vite config, API hooks
- **ml-engineer** → Elo logic, skill synthesis, quiz generation, recommendation scoring, graph algorithms
- **debugger** → tracebacks, build failures, runtime errors
- **code-reviewer** → runs after every change; checks architecture compliance, bugs, regressions

---

## Token Efficiency Rules

- Read `memory/project-memory.json` at session start — do not re-explore known architecture
- Read only the relevant router + service file for a given task — do not scan the entire `backend/` tree
- Check `memory/mistakes.json` before touching Elo logic, skill graph, or migration files
- Prefer reading `models/` before `routers/` — models reveal schema faster than router code

---

## Session Memory

At the end of every session, write a summary to `.claude/memory/session-log.json`:

```json
{
  "date": "YYYY-MM-DD",
  "built": "what was completed",
  "remaining": "what is still pending",
  "bugs_found": "any issues discovered",
  "decisions_made": "architectural choices made this session"
}
```

At the start of every session, read `.claude/memory/project-memory.json` and the most recent entry in `session-log.json` before doing anything else.
