# LearnPath AI — Complete Technical Documentation

> **Purpose:** End-to-end technical reference for the project author to understand and present the full system. Based entirely on the actual codebase.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Frontend Architecture](#3-frontend-architecture)
4. [Backend Architecture](#4-backend-architecture)
5. [Authentication Flow](#5-authentication-flow)
6. [GitHub Skill Ingestion](#6-github-skill-ingestion)
7. [Resume Skill Ingestion](#7-resume-skill-ingestion)
8. [Skill Profile System](#8-skill-profile-system)
9. [Roadmap System](#9-roadmap-system)
10. [Recommendation Engine](#10-recommendation-engine)
11. [XP + Level System](#11-xp--level-system)
12. [Quiz Generation System](#12-quiz-generation-system)
13. [AI Mentor](#13-ai-mentor)
14. [Performance Optimizations](#14-performance-optimizations)
15. [Example Request Flows](#15-example-request-flows)
16. [Important Files](#16-important-files)
17. [How to Debug the System](#17-how-to-debug-the-system)

---

## 1. Project Overview

**LearnPath AI** is an adaptive learning platform that solves "tutorial hell" — the common problem where developers bounce between random tutorials without a structured path.

The platform works by:

1. Analyzing a developer's **existing skills** from their GitHub profile and/or uploaded Resume PDF
2. Building a personalized **skill profile** with proficiency scores for each technology
3. Walking a **prerequisite course graph** (based on roadmap.sh-style curriculum data) to determine what is unlocked and what is not
4. **Recommending** the highest-priority unlocked course using a topology-aware scoring formula
5. Letting the user learn via **resources** (videos, articles), then take a **quiz** to prove understanding
6. Updating their **skill profile and XP** based on quiz performance
7. Providing an **AI Mentor** (powered by Google Gemini) that has live access to the user's learning state via tool calls

The entire experience is personalized — two users with different GitHub histories will receive completely different recommended learning paths through the same roadmap.

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        React Frontend (Vite)                        │
│  Pages: Dashboard, Roadmap, Course, Quiz, AI Mentor, Profile        │
│  Auth: Clerk JWT  |  Analytics: PostHog  |  Routing: React Router 7 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │  HTTPS REST API (Bearer JWT)
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       FastAPI Backend (Python)                      │
│  Routers → Services → Models                                        │
│  Auth: Clerk JWT verification (JWKS)                                │
│  Routers: users, courses, quiz, chat, github_auth, resume,          │
│           learning_path, recommend, skill_graph, roadmaps, events   │
└──────────┬───────────────────────────┬──────────────────────────────┘
           │ SQLAlchemy ORM            │ HTTP (httpx)
           ▼                           ▼
┌──────────────────────┐   ┌───────────────────────────────────────┐
│  PostgreSQL Database │   │         Google Gemini API             │
│  (Supabase-hosted)   │   │  Quiz generation + AI Mentor chat     │
│  Models: User,       │   │  Function-calling (MCP-style tools)   │
│  UserSkill, Course,  │   └───────────────────────────────────────┘
│  CoursePrerequisite, │
│  SkillProfile,       │   ┌───────────────────────────────────────┐
│  SkillWeight,        │   │         GitHub REST API               │
│  QuizAttempt,        │   │  Repos, languages, commits            │
│  Event, SkillQuiz    │   └───────────────────────────────────────┘
└──────────────────────┘
```

### Component Responsibilities

| Component | Technology | Responsibility |
|---|---|---|
| Frontend | React + Vite + TypeScript | UI, user interaction, auth token management |
| Backend | FastAPI (Python) | Business logic, auth enforcement, data access, AI calls |
| Database | PostgreSQL via SQLAlchemy | Persistent storage of users, skills, courses, quizzes, events |
| Gemini API | Google Generative AI | Quiz question generation, AI Mentor chat with tool use |
| GitHub API | GitHub REST v3 | Repo language bytes + commit counts for skill extraction |
| Clerk | Auth SaaS | User identity, JWT issuance, JWKS verification |
| PostHog | Analytics SaaS | Frontend event tracking (page views, button clicks) |

### Data Flow Summary

```
User signs up via Clerk
  → Frontend stores JWT
  → Backend creates User row (on first API call)
  → User connects GitHub / uploads Resume
  → Background job extracts skills → SkillWeight rows
  → synthesize_skill_profile() → SkillProfile rows
  → Dashboard shows recommended course from active roadmap
  → User takes quiz
  → QuizAttempt stored → XP awarded → SkillProfile updated
  → AI Mentor can query all of the above via tool calls
```

---

## 3. Frontend Architecture

### Technology Stack

- **React 18** with **TypeScript**
- **Vite** as the bundler
- **React Router v7** (declarative mode) for client-side routing
- **Tailwind CSS** + **shadcn/ui** for styling and UI components
- **Clerk** for authentication UI and JWT management
- **PostHog** for product analytics

### Routing

All routes are defined in `src/app/constants/routes.ts` and assembled in `src/app/App.tsx`. React Router v7 handles client-side navigation without full page reloads.

Key routes:

| Route | Page Component | Purpose |
|---|---|---|
| `/` | `LandingPage.tsx` | Marketing/welcome page |
| `/dashboard` | `DashboardPage.tsx` | Main hub after login |
| `/roadmaps` | `RoadmapCatalogPage.tsx` | Browse all available roadmaps |
| `/roadmap/:id` | `RoadmapPage.tsx` | View a specific roadmap graph |
| `/course/:id` | `CourseDetailPage.tsx` | Course detail, prerequisites, resources |
| `/quiz/:id` | `QuizPage.tsx` | Take a quiz for a course |
| `/ai-mentor` | `AIMentorPage.tsx` | Chat with the AI Mentor |
| `/profile` | `MyProfilePage.tsx` | GitHub connect, resume upload, skill stats |

### Main Pages

**DashboardPage.tsx**
- Fetches user profile (XP, level), skills, and recommended courses on mount
- Shows GitHub connection status with a "Sync" button that triggers re-extraction
- Displays the OnboardingWizard on first login
- Shows current roadmap progress and links to start/continue courses

**AIMentorPage.tsx**
- Conversational chat UI with user/assistant message bubbles
- Sends messages to `POST /chat` via `chatApi.ts`
- Shows animated typing indicator while waiting for a response
- Enter submits; Shift+Enter inserts a newline
- The backend does all the heavy lifting — the frontend only sends/receives text

**MyProfilePage.tsx**
- GitHub section: connect, disconnect, re-sync, shows language breakdown by weight
- Resume section: drag-and-drop upload, status indicator (not_uploaded / processing / ready)
- Skills section: shows top 5 skills from SkillProfile with proficiency bars
- Poll-based status updates while GitHub sync runs in the background

**RoadmapPage.tsx**
- Renders the course graph for a roadmap
- Calls `GET /roadmaps/:id/courses` and `GET /skill-graph/:roadmap_id/status`
- Courses are color-coded: completed (green), unlocked (blue), locked (grey)
- Clicking a course navigates to CourseDetailPage

**QuizPage.tsx**
- Fetches quiz questions from `GET /quiz/:skill_id` (answers hidden)
- User selects one option per question
- On submit, calls `POST /quiz/:skill_id/submit`
- Shows score, pass/fail, XP awarded, and any level-up notification

### API Service Layer

All API calls go through service files in `src/services/`. Each file wraps `fetch()` calls with the Clerk JWT token attached in the `Authorization: Bearer <token>` header.

```
src/services/
  api.ts            ← Base fetch wrapper; attaches Clerk JWT to every request
  userApi.ts        ← /users/me endpoints
  courseApi.ts      ← /courses endpoints
  roadmapApi.ts     ← /roadmaps endpoints
  chatApi.ts        ← /chat endpoint
  githubApi.ts      ← /github/* OAuth and sync
  resumeApi.ts      ← /resume upload
  progressApi.ts    ← /progress tracking
  dynamicRoadmapApi.ts ← /dynamic-roadmap status
```

The base URL is always read from `import.meta.env.VITE_API_URL` — never hardcoded.

### How UI Updates Based on Backend Responses

1. **Initial load:** Page component calls API on mount (inside `useEffect`), sets local state
2. **Mutations:** Button clicks (quiz submit, GitHub sync) call API, then re-fetch or merge returned data into state
3. **Background tasks:** GitHub sync is async — the frontend polls `GET /github/status` every few seconds until `sync_status === "completed"`
4. **Error states:** Failed API calls surface inline error messages; no global error boundary

---

## 4. Backend Architecture

### Directory Structure

```
backend/
  main.py               ← FastAPI app creation, CORS config, router registration
  config.py             ← Environment variable loading
  core/
    clerk_auth.py       ← JWT verification + user auto-creation
    rate_limit.py       ← Request rate limiting
    security.py         ← Security utilities
  db/
    database.py         ← SQLAlchemy engine, session factory, Base
  models/               ← ORM table definitions (one file per table)
  routers/              ← HTTP request handlers (thin layer, no business logic)
  services/             ← All business logic
  mcp_server/           ← AI Mentor tool definitions and dispatch
  migrations/           ← Alembic schema migrations
  scripts/              ← One-off data seeding / ingestion scripts
```

### main.py

`main.py` creates the FastAPI application, configures CORS (allowing the Vercel production URL and localhost for development), and registers all 14 routers with their URL prefixes:

```python
app.include_router(users_router,       prefix="/users")
app.include_router(courses_router,     prefix="/courses")
app.include_router(quiz_router,        prefix="/quiz")
app.include_router(chat_router,        prefix="/chat")
app.include_router(github_auth_router, prefix="/github")
app.include_router(resume_router,      prefix="/resume")
app.include_router(roadmaps_router,    prefix="/roadmaps")
# ... and more
```

### Routers (HTTP Layer)

Router files in `routers/` handle only HTTP concerns:
- Parse request body / path params / query params
- Call `get_current_user()` dependency to authenticate
- Delegate to a service function
- Return the service result

They contain **no business logic** — that all lives in `services/`.

Key routers:

| Router | Prefix | Key Endpoints |
|---|---|---|
| `users.py` | `/users` | GET /me, GET /me/profile, GET /me/skills, GET /me/github-analysis |
| `courses.py` | `/courses` | GET /, GET /:id, GET /:id/roadmap |
| `quiz.py` | `/quiz` | GET /:skill_id, POST /:skill_id/submit |
| `chat.py` | `/chat` | POST / (AI Mentor) |
| `github_auth.py` | `/github` | GET /connect, GET /callback, POST /sync, DELETE /disconnect |
| `resume.py` | `/resume` | POST / (upload), GET /status |
| `roadmaps.py` | `/roadmaps` | GET /, GET /:id, GET /:id/courses |
| `learning_path.py` | `/learning-path` | GET /:roadmap_id/recommend |
| `skill_graph.py` | `/skill-graph` | GET /:roadmap_id, GET /:roadmap_id/status |
| `events.py` | `/events` | POST / (log event) |

### Services (Business Logic)

Services in `services/` contain all the real logic. They receive a SQLAlchemy `Session` object and return plain Python dicts or ORM objects.

| Service File | What It Does |
|---|---|
| `skill_synthesizer.py` | Merges SkillWeight rows (from GitHub, resume, quiz) into a unified SkillProfile |
| `learning_priority_service.py` | Computes which courses are unlocked and ranks them by importance score |
| `quiz_service.py` | Scores quiz submissions, emits course_completed event, triggers XP + skill updates |
| `quiz_generation_service.py` | Calls Gemini to generate quiz questions; caches results in SkillQuiz table |
| `skill_graph_service.py` | Graph traversal: checks if a course is unlocked, completed, or locked |
| `github_skill_extractor.py` | Fetches GitHub repos, maps language bytes + commits to SkillWeight rows |
| `resume_parser.py` | Extracts text from PDF, frequency-matches skill keywords, creates SkillWeight rows |
| `skill_profile_service.py` | Updates SkillProfile after quiz completion using a weighted EMA formula |
| `xp_level_service.py` | Awards XP for quiz performance; recalculates user level from total XP |
| `course_level_service.py` | Manages required level per course for gating access |
| `dynamic_roadmap_service.py` | Generates dynamic roadmap states based on user progress |
| `video_content_service.py` | Handles video resource metadata |

### Models (Database Layer)

Models in `models/` are SQLAlchemy ORM classes, one per database table. See Section 9 for the full schema breakdown.

### mcp_server/ (AI Tool Layer)

The `mcp_server/` directory implements a tool-use pattern similar to the Model Context Protocol:

- `tools.py` — 5 Python functions that query the database directly (each opens its own session)
- `registry.py` — Gemini function declarations (JSON schema) and a dispatch table mapping tool names to Python callables

These tools are passed to Gemini on every AI Mentor chat request so the model can call them to retrieve real user data before answering.

---

## 5. Authentication Flow

### Technology

Authentication is handled entirely by **Clerk**, a third-party auth provider. Clerk issues RS256-signed JWTs containing the user's `clerk_user_id`.

### Step-by-Step Flow

```
1. User visits the app
2. Clerk's React SDK renders the login UI (sign-in/sign-up)
3. User authenticates (email/password or OAuth)
4. Clerk issues a JWT (RS256 signed) to the frontend
5. Frontend stores the JWT in memory (Clerk manages this)

6. Frontend makes an API call:
   GET /users/me
   Authorization: Bearer <clerk_jwt>

7. Backend receives the request
8. get_current_user() dependency runs:
   a. Extracts the JWT from the Authorization header
   b. Fetches Clerk's JWKS (JSON Web Key Set) endpoint to get the public key
   c. JWKS is cached in memory with a 1-hour TTL (thread-safe)
   d. Verifies the JWT signature using the cached public key
   e. Extracts clerk_user_id from the token payload
   f. Queries the database: SELECT * FROM users WHERE clerk_user_id = ?
   g. If the user does NOT exist → auto-creates a User row with default values
      (global_elo_rating=800, total_xp=0, current_level=1)
   h. Returns the User ORM object

9. The router function receives the verified User object and proceeds
```

### Key File: `backend/core/clerk_auth.py`

```python
# Simplified view of what happens
def get_current_user(token: str, db: Session) -> User:
    payload = verify_clerk_token(token)      # RS256 verify with cached JWKS
    clerk_id = payload["sub"]                # Extract user identifier
    user = db.query(User).filter(
        User.clerk_user_id == clerk_id
    ).first()
    if not user:
        user = User(clerk_user_id=clerk_id, ...)
        db.add(user); db.commit()
    return user
```

### Security Notes

- The JWKS cache rotates automatically after 1 hour
- The backend never stores passwords — Clerk manages credentials
- The `user_id` in tool calls (AI Mentor) is always overridden with the authenticated user's actual ID, preventing the LLM from being tricked into querying another user's data

---

## 6. GitHub Skill Ingestion

### Purpose

When a user connects their GitHub account, the system fetches their repositories, analyzes the languages they've written, and converts that into skill proficiency scores.

### OAuth Flow

```
1. User clicks "Connect GitHub" on the profile page
2. Frontend calls GET /github/connect
3. Backend generates a random OAuth state token (10-minute TTL), stores it in oauth_state table
4. Backend returns a GitHub OAuth authorization URL
5. Frontend redirects the user to github.com/login/oauth/authorize
6. User approves the OAuth app on GitHub
7. GitHub redirects back to GET /github/callback?code=...&state=...
8. Backend validates the state token (anti-CSRF)
9. Backend exchanges the code for a GitHub access token via POST to github.com/login/oauth/access_token
10. Stores the access token in User.github_access_token
11. Launches a background task: extract_github_skills(user_id, access_token)
12. Returns immediately to the frontend (sync happens asynchronously)
```

### Skill Extraction (Background Task)

The background task in `services/github_skill_extractor.py` runs these steps:

```
1. Fetch all non-forked, non-archived repositories for the user
   GET https://api.github.com/user/repos

2. For each repo, get language byte counts
   GET https://api.github.com/repos/{owner}/{repo}/languages
   Example: {"Python": 45230, "JavaScript": 8100}

3. Also fetch commit count per repo (to weight active contributors more)

4. Compute a combined weight per language:
   combined_weight = (byte_weight × 0.6) + (commit_weight × 0.4)

5. Map language names to roadmap skill IDs:
   "Python"     → "python-developer"
   "JavaScript" → "javascript"
   "TypeScript" → "typescript"
   "Go"         → "golang"
   etc.

6. Normalize all weights to 0–1 range

7. Insert/update SkillWeight rows:
   INSERT INTO skill_weights (user_id, skill_name, source, weight, confidence)
   VALUES (?, ?, 'github', ?, ?)
   ON CONFLICT → UPDATE

8. Call synthesize_all_skills_for_user(user_id)
   → Merges all SkillWeights into SkillProfile rows

9. Update User.github_sync_status = "completed" (or "failed")
```

### Where Results Go

After extraction, the user's skills are stored as:
- **SkillWeight** rows (raw input, source = "github")
- **SkillProfile** rows (synthesized output, after merging with resume/quiz data)

---

## 7. Resume Skill Ingestion

### Upload Flow

```
1. User uploads a PDF resume via drag-and-drop on the profile page
2. Frontend sends POST /resume (multipart/form-data)
3. Backend receives the PDF bytes
4. Sets User.resume_status = "processing"
5. Calls extract_text_from_pdf() → pdfplumber extracts raw text
6. Calls extract_skills_from_text() → regex frequency matching
7. Stores SkillWeight rows with source = "resume"
8. Calls synthesize_skill_profile() to update SkillProfile
9. Updates User.resume_status = "ready"
```

### Skill Extraction Logic

`services/resume_parser.py` uses a `RESUME_SKILL_MAP` dictionary that maps skill keywords to roadmap skill IDs:

```python
RESUME_SKILL_MAP = {
    "python": "python-developer",
    "javascript": "javascript",
    "react": "react",
    "node": "nodejs",
    "docker": "docker",
    # ... many more
}
```

For each skill keyword found in the resume text:
- Count occurrences (frequency)
- `weight = occurrence_count / max_occurrences` (normalized 0–1)
- `confidence = min(1.0, occurrence_count / 5.0)` (capped at 1.0)

### Difference from GitHub Ingestion

| Dimension | GitHub | Resume |
|---|---|---|
| Signal type | Actual code written | Self-reported text |
| Trust multiplier in synthesis | 1.0× | 0.6× |
| Confidence source | Language bytes + commits | Keyword frequency |
| Async? | Yes (background task) | No (synchronous) |

---

## 8. Skill Profile System

### What Is a SkillProfile?

A `SkillProfile` row represents the synthesized, unified view of a user's proficiency in a specific skill (which maps 1:1 to a course ID).

```
SkillProfile columns:
  user_id           → which user
  skill_id          → the course ID this maps to (e.g. "python-developer:variables")
  roadmap_id        → which roadmap (e.g. "python-developer")
  proficiency_level → 0.0 – 1.0 synthesized score
  confidence        → 0.0 – 1.0 how much we trust this proficiency
  github_proficiency, github_confidence  → from GitHub source
  resume_proficiency, resume_confidence  → from resume source
  quiz_proficiency, quiz_confidence      → from quiz performance
  updated_at        → last synthesis timestamp
```

### How Skills Are Synthesized

The `skill_synthesizer.py` service merges all SkillWeight rows for a user into SkillProfile rows.

**Source multipliers:**

| Source | Multiplier | Reason |
|---|---|---|
| GitHub | 1.0× | Actual code written — strong signal |
| Resume | 0.6× | Self-reported — weaker signal |
| Quiz | 1.3× | Directly tested — strongest signal |
| Engagement | 1.1× | Interaction data |

**Synthesis formula (simplified):**

```python
weighted_proficiency = sum(weight * confidence * multiplier for each source)
total_weight = sum(confidence * multiplier for each source)
proficiency_level = weighted_proficiency / total_weight
```

### How Proficiency Affects Recommendations

The proficiency score feeds into the recommendation engine via a **confidence adjustment**:

- If `confidence < 0.4` (weak skill): **+5.0 priority boost** → system pushes you toward this skill
- If `confidence > 0.7` (strong skill): **−3.0 priority penalty** → system de-prioritizes this skill

This means: if you have weak Python skills but are on the Python roadmap, Python courses get bumped up in priority.

---

## 9. Roadmap System

### Course Storage

Courses are stored in the `courses` table with a composite primary key:

```
Course.id = "{roadmap_id}:{node_id}"
Example: "python-developer:variables"
         "frontend:html-basics"
```

Additional columns:
- `roadmap_id` — which roadmap this belongs to (e.g. `"python-developer"`)
- `title` — human-readable course name
- `description` — content description
- `difficulty_level` — computed as `800 + (topological_depth × 100)`
- `required_level` — minimum user level to unlock (1–6)

### Prerequisite Graph

The `course_prerequisites` table defines a **Directed Acyclic Graph (DAG)**:

```
course_prerequisites:
  course_id       → the dependent course (what needs unlocking)
  prerequisite_id → what must be completed first

Example:
  course_id="python:functions", prerequisite_id="python:variables"
  → "variables" must be done before "functions"
```

This is the fundamental structure used by the recommendation engine.

### Course Resources

Each course can have multiple learning resources in the `course_resources` table:

```
course_resources:
  course_id     → links to Course
  resource_type → "video", "article", "documentation", "interactive"
  url           → the resource URL
  title         → display title
```

### Roadmap Progression

```
1. User selects a roadmap (e.g. "Python Developer")
2. Backend fetches all Course rows for that roadmap
3. Backend fetches all CoursePrerequisite edges
4. For each course:
   - Check if all prerequisites are in the user's completed_ids set
   - If yes → UNLOCKED (can be studied)
   - If no  → LOCKED (prerequisites not met)
   - If in completed_ids → COMPLETED
5. The frontend renders the graph with color-coded states
```

---

## 10. Recommendation Engine

**File:** `backend/services/learning_priority_service.py`

### What It Solves

Given a user and a roadmap, find the single best course to study next. The answer depends on:
1. What they've already completed (prerequisite satisfaction)
2. Which unlocked course unlocks the most future learning (topology)
3. What their current skill gaps are (confidence adjustment)

### The Algorithm

```
Step 1 — Find all unlocked courses
  A course is unlocked if:
  - ALL of its prerequisite courses are in the user's completed set
  - AND the course itself has NOT been completed yet

Step 2 — Score each unlocked course
  For each unlocked course:
    out_degree = number of courses that depend on THIS course (direct children)
    descendants = total courses reachable downstream via BFS
    depth = longest prerequisite chain to reach this course from a root
    
    base_score = (descendants × 3) + (out_degree × 2) + (10 − depth)
    
    confidence_adj = 0.0
    if user confidence for this skill < 0.4: confidence_adj = +5.0
    if user confidence for this skill > 0.7: confidence_adj = −3.0
    
    final_score = base_score + confidence_adj

Step 3 — Sort descending, return top 1 + 2 alternatives
```

### Why This Formula Works

- **High descendants** → completing this course unlocks many future courses. Study it first.
- **High out_degree** → directly enables many next steps. Good gateway.
- **Low depth** → closer to the root. Foundational knowledge. Prefer it over advanced topics.
- **Low confidence** → the user needs work here. Boost its priority.
- **High confidence** → user already knows this. De-prioritize.

### Batched Implementation

The production version (`get_recommended_start_courses_batched`) executes exactly **4 SQL queries** regardless of roadmap size, then resolves everything in Python memory — avoiding the N+1 problem:

```
Q1: All Course rows for roadmap_id
Q2: All CoursePrerequisite edges for those courses
Q3: All completed/skipped events + passed quiz attempts (UNION ALL)
Q4: All SkillProfile rows for this user
→ Everything else is in-memory graph traversal
```

---

## 11. XP + Level System

**File:** `backend/services/xp_level_service.py`

### XP Award Logic

XP is awarded when a user passes a quiz. The amount depends on how deep in the course graph the course sits (more advanced = more XP):

```python
xp_for_course = topological_depth * 20 + 10

# Score thresholds:
if quiz_score >= 0.8:  xp_awarded = full_xp        # 80%+ → full XP
elif quiz_score >= 0.5: xp_awarded = full_xp // 2  # 50–79% → half XP
else:                  xp_awarded = 0               # < 50% → no XP
```

Examples:
- Root course (depth=0): `0 × 20 + 10 = 10 XP`
- One level deep (depth=1): `1 × 20 + 10 = 30 XP`
- Advanced course (depth=5): `5 × 20 + 10 = 110 XP`

### Level Thresholds

| Level | Label | Total XP Required |
|---|---|---|
| 1 | Novice | 0 |
| 2 | Apprentice | 150 |
| 3 | Practitioner | 400 |
| 4 | Expert | 650 |
| 5 | Master | 850 |
| 6 | Grandmaster | 1000+ |

### Level Calculation

```python
_LEVEL_THRESHOLDS = [0, 150, 400, 650, 850, 1000]

def compute_level_from_xp(xp: int) -> int:
    level = 1
    for threshold in _LEVEL_THRESHOLDS:
        if xp >= threshold:
            level += 1
        else:
            break
    return min(6, max(1, level - 1))
```

Level is always recomputed deterministically from total XP — there's no separate "level up" event.

### XP Storage

- `User.total_xp` — global XP across all roadmaps
- `User.current_level` — recomputed from total_xp
- `UserSkill.xp` — XP scoped to a specific roadmap/skill
- `UserSkill.level` — level within that specific skill

---

## 12. Quiz Generation System

**File:** `backend/services/quiz_generation_service.py`

### Overview

When a user starts a quiz for a course, the backend either retrieves a cached quiz or generates a new one using Google Gemini.

### Step-by-Step Flow

```
1. User navigates to /quiz/:skill_id
2. Frontend calls GET /quiz/:skill_id
3. Backend calls get_or_generate_quiz(skill_id, db)

4. Check cache: SELECT * FROM skill_quizzes WHERE skill_id = ?
5. If cached quiz exists → return it (skip generation)

6. If no cached quiz:
   a. Construct a prompt for Gemini:
      "Generate a multiple-choice quiz for the topic: {course_title}
       Include 4-6 questions, each with 4 options and one correct answer."
   
   b. Call Gemini API (gemini-3-flash):
      - Temperature: 0.4 (more deterministic than creative tasks)
      - Request JSON output
   
   c. Parse the response:
      - Try to extract JSON from markdown code blocks first
      - Fall back to raw text JSON parsing
      - Validate: must have 4–6 questions, each with 4 options
   
   d. On parse failure → return static fallback quiz
   
   e. On success:
      - Store in SkillQuiz table (cached for future users)
      - Handle race conditions (another request may have inserted first)

7. Return questions to frontend WITHOUT correct_answer field (anti-cheat)
```

### Anti-Cheat Mechanism

The `GET /quiz/:skill_id` endpoint strips the `correct_answer` field from each question before returning it. The correct answers only exist server-side in the `SkillQuiz.questions` JSON blob.

### Quiz Submission and Scoring

```
1. User submits answers: POST /quiz/:skill_id/submit
   Body: {"answers": {"q1": "option_a", "q2": "option_c", ...}}

2. Backend loads the cached quiz (with correct answers)
3. For each question:
   user_answer == correct_answer → +1 point

4. score = (correct / total) * 100

5. passed = score >= quiz.passing_score  (default: 75%)

6. If passed:
   - Insert Event(event_type="course_completed")
   - Call award_xp_for_quiz() → updates User.total_xp, User.current_level
   - Call update_skill_profile_from_quiz() → updates SkillProfile

7. Store QuizAttempt row (for history)

8. Return: {score, passed, xp_awarded, total_xp, current_level}
```

---

## 13. AI Mentor

**Files:** `backend/routers/chat.py`, `backend/mcp_server/tools.py`, `backend/mcp_server/registry.py`

### What the AI Mentor Is

The AI Mentor is a conversational assistant powered by Google Gemini with the ability to query live user data via a tool-use (function-calling) pattern inspired by the Model Context Protocol (MCP). It can answer questions like "What should I study next?", "How much progress have I made?", and "Explain this concept to me."

### Architecture Pattern

```
User message → Backend → Gemini (with tool declarations) → Tool calls → DB queries → Gemini (with data) → Reply
```

The key insight: Gemini doesn't get raw database access. Instead, the backend defines 5 typed Python functions as **tools**. Gemini can request to call any of these, the backend executes them, and feeds the results back to Gemini.

### The 5 MCP Tools

Defined in `mcp_server/tools.py`:

| Tool Name | What It Returns |
|---|---|
| `get_user_profile` | User's skills, Elo rating, XP, level, GitHub connection status |
| `get_user_progress` | Completed courses per roadmap with progress percentages |
| `get_next_course` | Top recommended course + 2 alternatives for a given roadmap |
| `get_roadmap_courses` | All courses in a roadmap ordered by difficulty |
| `get_skill_graph` | Prerequisite edges ± per-skill completion status |

Each tool opens its own database session, queries the DB, closes the session, and returns a plain dict.

### System Prompt + Context Injection

Before any Gemini call, the backend builds a **user context snapshot** (`build_user_context()`) that is injected into the system prompt:

```
## Learner Context (live data — do not ask the user to confirm these details)
- Level: 3 (Practitioner) | XP: 520
- Active roadmap: python-developer
- Next recommended course: Python Functions [python-developer:functions]
- Alternatives: Loops, Conditionals
- Total courses completed: 7
- Top skills: python (0.82), javascript (0.65), html (0.55)
- GitHub: connected (@johndoe)
```

This means Gemini can answer common questions **without any tool calls** — the context is already there.

### The Function-Calling Loop

```python
# backend/routers/chat.py (simplified)

for _ in range(MAX_TOOL_ROUNDS):  # max 5 rounds
    response = await gemini.generate(
        system_prompt = SYSTEM_PROMPT + user_context,
        tools = TOOL_DECLARATIONS,
        contents = conversation_history
    )
    
    if response has function_calls:
        # Append model's tool-call request to conversation
        conversation_history.append(model_turn)
        
        # Execute each tool
        for function_call in response.function_calls:
            # SECURITY: Override user_id with authenticated user's actual ID
            if function_call.name in USER_ID_TOOLS:
                function_call.args["user_id"] = authenticated_user_id
            
            # Look up and call the tool
            tool_fn = TOOL_REGISTRY[function_call.name]
            result = tool_fn(**function_call.args)
            
        # Feed results back to Gemini
        conversation_history.append(tool_results_turn)
        continue  # Let Gemini respond with real data
    
    else:
        # No more tool calls — extract text and return
        return ChatResponse(reply=response.text)
```

### Model Fallback Chain

```
Attempt 1: gemini-3-flash-preview (primary)
  → If 503 or timeout → 
Attempt 2: gemini-2.5-flash (fallback)
  → If 503 or timeout →
Attempt 3: gemini-2.5-flash (retry)
  → If all fail → graceful error message
```

### Security

The `USER_ID_TOOLS` frozenset (`get_user_profile`, `get_user_progress`, `get_next_course`, `get_skill_graph`) always have their `user_id` argument **overridden** by the authenticated user's ID before dispatch. This prevents prompt injection attacks where a malicious message might instruct Gemini to query a different user's data.

---

## 14. Performance Optimizations

### Batched Recommendation Queries

The original recommendation algorithm queried the database once per course to check prerequisites — an N+1 problem. For a roadmap with 50 courses, that was 50+ queries.

The batched version (`get_recommended_start_courses_batched`) executes exactly **4 queries** regardless of roadmap size:

```
Before: 50+ queries (1 per course for prerequisite check + graph traversal)
After:  4 queries   (all courses, all edges, all completed IDs, all skill profiles)
```

All graph traversal (BFS descendant counting, depth calculation, unlock resolution) happens in Python dictionaries after the data is fetched.

### Aggregated Progress Queries

`GET /users/me/skills` uses batched queries to compute progress per roadmap:
- Fetches all UserSkill rows in a single query
- Computes progress percentages in Python, not per-roadmap SQL
- No N+1 queries across roadmaps

### JWKS Caching

Clerk's public keys (JWKS) are fetched once and cached in memory for 1 hour. This avoids an HTTP round-trip to Clerk's servers on every single authenticated API request.

### Quiz Caching

Generated quizzes are stored in the `skill_quizzes` table. Once generated for a course, the same questions are served to all users — Gemini is only called once per course (or never, if a quiz already exists).

### Memoized Depth Calculation

In the batched recommendation function, `compute_depth(node)` memoizes results in a local dict, preventing redundant recursive traversal of shared prerequisite chains.

---

## 15. Example Request Flows

### Flow 1: User Opens Dashboard

```
1. Browser loads /dashboard
2. DashboardPage.tsx mounts
3. Parallel API calls:
   - GET /users/me            → User profile (XP, level, status flags)
   - GET /users/me/skills     → Skills with roadmap progress %
   - GET /courses?roadmap_id=X → (if roadmap selected) Courses with recommendation
4. Backend for GET /users/me:
   - clerk_auth.py verifies JWT
   - Returns User row as JSON
5. Backend for GET /users/me/skills:
   - Fetches UserSkill rows (1 query)
   - Fetches Course counts per roadmap (1 query per roadmap)
   - Fetches completed event counts (1 query)
   - Returns skill name, proficiency, roadmap progress %
6. Frontend sets state with responses
7. React re-renders: shows XP bar, skill list, recommended course card
```

### Flow 2: User Asks AI Mentor "What should I study next?"

```
1. User types "What should I study next?" and presses Enter
2. AIMentorPage.tsx calls chatApi.sendChatMessage("What should I study next?")
3. POST /chat { "message": "What should I study next?" }

4. Backend: chat.py router executes
   a. Verifies JWT → gets User object
   b. build_user_context(user_id) runs:
      - Fetches User row (XP, level, GitHub status)
      - Fetches top 5 UserSkill by proficiency
      - Finds most recent Event with a roadmap reference → active roadmap
      - Calls get_recommended_start_courses_batched() → next course
      - Builds plain-text context block
   c. Injects context into system prompt

5. Gemini API call:
   - System prompt: "You are an AI learning mentor... [user context block]"
   - User message: "What should I study next?"
   - Tools: [5 function declarations]
   - Temperature: 0.7

6. Gemini responds without tool calls (context already has the answer):
   "Based on your current progress, I recommend studying Python Functions next.
    You're at Level 3 with 520 XP and have completed 7 courses.
    Python Functions will unlock 8 downstream topics including decorators and modules."

7. Backend returns ChatResponse(reply=...)
8. Frontend appends the reply to the conversation UI
```

### Flow 3: User Completes a Quiz

```
1. User answers all questions on /quiz/python-developer:functions
2. Frontend calls POST /quiz/python-developer:functions/submit
   Body: {"answers": {"0": "def keyword", "1": "return", ...}}

3. Backend: quiz.py router
   a. Verifies JWT
   b. Loads SkillQuiz for skill_id (with correct answers)
   c. Compares each answer: 4/5 correct → score = 80
   d. passed = 80 >= 75 → True
   e. award_xp_for_quiz(user_id, 0.8, course_id, roadmap_id):
      - Looks up course depth (= 2)
      - full_xp = 2 * 20 + 10 = 50
      - quiz_score 0.8 >= 0.8 → xp_award = 50
      - User.total_xp += 50
      - User.current_level = compute_level_from_xp(570) → 3
      - UserSkill.xp += 50
   f. update_skill_profile_from_quiz():
      - quiz_confidence += 0.2 (capped at 1.0)
      - Recomputes proficiency using weighted EMA
   g. Inserts Event(event_type="course_completed", course_id=..., roadmap_id=...)
   h. Inserts QuizAttempt row

4. Returns:
   {
     "score": 80,
     "passed": true,
     "xp_awarded": 50,
     "total_xp": 570,
     "current_level": 3
   }

5. QuizPage.tsx shows: "Passed! +50 XP" with level indicator
6. Next visit to dashboard shows updated recommendation (functions now completed)
```

---

## 16. Important Files

### Backend

| File | Why It Matters |
|---|---|
| `backend/main.py` | Entry point; where all routers are registered |
| `backend/core/clerk_auth.py` | All authentication flows through here |
| `backend/services/learning_priority_service.py` | The recommendation engine — the core algorithm |
| `backend/services/skill_synthesizer.py` | How GitHub + resume + quiz data becomes a skill profile |
| `backend/services/github_skill_extractor.py` | How GitHub repos become skill weights |
| `backend/services/quiz_generation_service.py` | Gemini integration for quiz creation |
| `backend/services/xp_level_service.py` | XP award formulas and level thresholds |
| `backend/mcp_server/tools.py` | The 5 tools the AI Mentor can call |
| `backend/mcp_server/registry.py` | Gemini function declarations + dispatch table |
| `backend/routers/chat.py` | The AI Mentor endpoint — full function-calling loop |
| `backend/routers/quiz.py` | Quiz fetch (answers hidden) + submission + scoring |

### Frontend

| File | Why It Matters |
|---|---|
| `src/app/App.tsx` | Route definitions |
| `src/services/api.ts` | Base fetch wrapper with JWT injection |
| `src/app/pages/DashboardPage.tsx` | Main user experience hub |
| `src/app/pages/AIMentorPage.tsx` | AI Mentor chat interface |
| `src/app/pages/QuizPage.tsx` | Quiz interface |
| `src/app/pages/MyProfilePage.tsx` | GitHub connect + resume upload |

### Models

| File | Why It Matters |
|---|---|
| `backend/models/user.py` | Central entity with XP, level, GitHub/resume status |
| `backend/models/skill_profile.py` | Synthesized skill proficiency (drives recommendations) |
| `backend/models/skill_weight.py` | Raw input signals from each data source |
| `backend/models/course.py` | The course graph nodes |
| `backend/models/course_prerequisite.py` | The course graph edges |
| `backend/models/event.py` | Completion/skip events — drives unlock logic |
| `backend/models/quiz_attempt.py` | Quiz history |
| `backend/models/skill_quiz.py` | Cached generated quiz questions |

---

## 17. How to Debug the System

### Backend Issues

**Start the backend with verbose logging:**
```bash
cd backend
uvicorn main:app --reload --port 8000 --log-level debug
```

**Check that all environment variables are set:**
```bash
# Required in backend/.env
DATABASE_URL=postgresql://...
CLERK_SECRET_KEY=sk_...
GEMINI_API_KEY=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
```

**Test authentication manually:**
```bash
# Get a token from the frontend (browser dev tools → Network tab → any API request → Authorization header)
curl -H "Authorization: Bearer <token>" http://localhost:8000/users/me
```

**Check if a route is registered:**
```bash
curl http://localhost:8000/openapi.json | python3 -m json.tool | grep '"path"'
```

### Database Issues

**Run pending migrations:**
```bash
cd backend
alembic upgrade head
```

**Check current migration state:**
```bash
alembic current
alembic history
```

**Connect directly to check data:**
```bash
psql $DATABASE_URL
\dt                          -- list tables
SELECT * FROM users LIMIT 5;
SELECT * FROM skill_profiles WHERE user_id = '...';
SELECT * FROM events WHERE user_id = '...' ORDER BY created_at DESC LIMIT 10;
```

**Debug recommendation engine:**
The recommendation uses 4 queries. Add logging to `get_recommended_start_courses_batched()`:
- Print `len(courses)` → are courses loaded for this roadmap?
- Print `len(completed_ids)` → has the user completed anything?
- Print `unlocked_ids` → are any courses unlocked?
- If `unlocked_ids` is empty and it shouldn't be: check that prerequisite completion events exist

### AI Mentor Issues

**Symptom: Mentor always says it can't help**
- Check `GEMINI_API_KEY` is set in backend `.env`
- Check backend logs for `_GeminiUnavailable` or `TimeoutException`
- Try the fallback model directly: change `_PRIMARY_MODEL` to `gemini-2.5-flash`

**Symptom: Mentor gives wrong information about the user**
- Check `build_user_context()` output: add a temporary `print(user_context)` at the top of the chat endpoint
- Verify the user has events in the `events` table (needed to determine active roadmap)
- Verify `UserSkill` rows exist for the user

**Symptom: Tool calls never execute**
- Check `TOOL_REGISTRY` in `mcp_server/registry.py` — all 5 tools must be registered
- Add logging before `tool_fn(**args)` in `chat.py` to confirm dispatch
- Check that Gemini is returning `functionCall` parts — log `function_calls` list

### Gemini API Failures

**Rate limits (HTTP 429):**
- Gemini has per-minute quotas. Slow down quiz generation requests.
- Quiz caching (SkillQuiz table) prevents repeated calls — check if caching is working.

**Quiz generation produces invalid JSON:**
- The parser tries markdown code blocks first, then raw JSON
- Add logging in `quiz_generation_service.py` to print the raw Gemini response
- The fallback static quiz activates on parse failure — check logs for `"falling back to static quiz"`

**Model unavailable (HTTP 503):**
- The chat endpoint has a 3-attempt fallback chain (primary + 2 fallback attempts)
- Check backend logs: `"attempt N returned 503 — retrying with ..."`
- If all 3 attempts fail, the endpoint returns a graceful error message (not an HTTP error)

### GitHub Sync Issues

**Symptom: Sync stuck at "processing"**
- GitHub extraction runs as a `BackgroundTasks` task in FastAPI
- Check backend logs for errors from `extract_github_skills()`
- Common cause: GitHub access token expired or revoked
- Fix: user disconnects and reconnects GitHub

**Symptom: No skills extracted after sync**
- Check if the user's repos are not archived or forked (both are filtered out)
- Check if their repos use languages that are in the `LANGUAGE_TO_SKILL_MAP` in `github_skill_extractor.py`
- Verify `SkillWeight` rows were inserted: `SELECT * FROM skill_weights WHERE user_id = '...' AND source = 'github'`
- Verify `synthesize_skill_profile()` ran: check for `SkillProfile` rows

### Frontend Issues

**API calls returning 401:**
- Clerk token may be expired — the `TokenSynchronizer` should refresh it automatically
- Check the browser console for `"Token refresh failed"` messages

**Dashboard shows no recommendation:**
- User may not have selected a roadmap yet
- Call `GET /learning-path/:roadmap_id/recommend` directly in the browser with a valid token to test

**Quiz answers not submitting:**
- Open browser dev tools → Network tab → check the POST request body
- Ensure all questions have an answer selected before submit
- Check the response body for error details
