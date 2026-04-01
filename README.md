# LearnPath AI

An adaptive learning platform that eliminates "tutorial hell" by analysing a developer's existing skills and generating a personalised, dependency-aware learning curriculum — powered by Google Gemini.

---

## Overview

Most developers stuck in tutorial hell know *what* they want to learn but have no structured path to get there. Generic roadmaps treat everyone the same. LearnPath AI solves this by:

1. **Analysing what you already know** — via your GitHub profile and uploaded resume.
2. **Building a personalised skill graph** — a prerequisite-aware dependency map of topics.
3. **Recommending what to learn next** — ranked by how much a topic unlocks downstream learning.
4. **Adapting over time** — an Elo-based rating system updates your skill profile after every quiz.
5. **Answering your questions** — an AI Mentor powered by Gemini has live access to your real progress data.

---

## Key Features

### Personalised Learning Roadmap
Roadmaps are structured as directed acyclic graphs where each course has prerequisites. The system walks this graph and only surfaces topics you are ready to start. Completing a topic automatically unlocks its dependents.

### Elo + XP Levelling System
Every quiz updates your per-skill Elo rating using the standard logistic formula (K = 32, bounds 800–2000). A global XP system tracks cumulative progress across six levels:

| Level | Name |
|---|---|
| 1 | Novice |
| 2 | Apprentice |
| 3 | Practitioner |
| 4 | Expert |
| 5 | Master |
| 6 | Grandmaster |

### Skill Graph & Dependency Tracking
Course prerequisites are sourced from roadmap.sh JSON data and stored as a graph of directed edges. BFS traversal determines which topics are completed, unlocked, or locked for each user.

### Course Recommendation Engine
Unlocked courses are ranked by an importance score:

```
importance_score = (descendant_count × 3) + (out_degree × 2) + (10 − graph_depth)
```

The top-ranked course is marked as "recommended"; the next two become "alternatives". This surfaces the topic that unlocks the most future learning.

### AI Mentor (Gemini-Powered)
A conversational AI mentor with live access to your learning data. When you ask "What should I study today?", the mentor:
- Pre-loads your active roadmap, XP, level, top skills, and next recommended course before calling the model — no user input needed.
- Can invoke backend tools during the conversation (Gemini function calling) for deeper queries.
- Always responds with real data — never fabricated statistics.

### MCP-Style Tool Architecture
The AI Mentor uses an in-process Model Context Protocol (MCP) style tool registry. Five tools are available to the Gemini model during a conversation:

| Tool | Description |
|---|---|
| `get_user_profile` | Skills, Elo rating, XP, level, GitHub status |
| `get_user_progress` | Completed courses per roadmap with progress percentages |
| `get_next_course` | Top recommendation + alternatives for a given roadmap |
| `get_roadmap_courses` | All courses in a roadmap ordered by difficulty |
| `get_skill_graph` | Prerequisite edges; optionally with per-skill completion status |

### GitHub Skill Extraction
Connecting GitHub triggers an OAuth flow that fetches all non-forked, non-archived repositories, maps language byte counts and commit history to skill weights, and synthesises them into a ranked skill profile. The sync runs as a background task and can be re-triggered from the profile page.

### Resume Parsing
Uploading a PDF resume extracts raw text via `pdfplumber` and applies regex-based skill matching to identify known technologies. Extracted skills are merged with GitHub-derived weights into a unified skill profile.

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  React Frontend (Vite + TypeScript)                      │
│  Clerk Auth │ PostHog Analytics │ React Router v7        │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTPS + Clerk JWT
┌──────────────────────▼──────────────────────────────────┐
│  FastAPI Backend (Python)                                │
│                                                          │
│  Routers → Services → SQLAlchemy ORM                    │
│                                                          │
│  ┌───────────────────────────────────────────────────┐  │
│  │  AI Mentor  POST /chat                            │  │
│  │                                                    │  │
│  │  1. build_user_context()  ← DB queries            │  │
│  │     active roadmap · XP · top skills ·            │  │
│  │     next recommended course                       │  │
│  │                                                    │  │
│  │  2. Gemini API (gemini-3-flash-preview)            │  │
│  │     system_prompt + live context injected         │  │
│  │     function_declarations → optional tool calls   │  │
│  │                                                    │  │
│  │  3. MCP Tool Registry (if tools called)           │  │
│  │     dispatch → DB queries → results → Gemini      │  │
│  │                                                    │  │
│  │  4. Final text reply → frontend                   │  │
│  └───────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────┘
                       │ SQLAlchemy
┌──────────────────────▼──────────────────────────────────┐
│  PostgreSQL (Supabase)                                   │
└──────────────────────────────────────────────────────────┘
```

### Context Injection
Before calling Gemini, the backend runs `build_user_context()` — a single-session DB read that produces a compact plain-text snapshot of the user's current state. This is injected into the Gemini system prompt so the model can answer common questions instantly without tool-call round-trips.

### Model Fallback Chain
On `503 UNAVAILABLE` or timeout, the endpoint automatically retries with the fallback model. All switches are logged.

```
Attempt 1: gemini-3-flash-preview
Attempt 2: gemini-2.5-flash          ← on 503 or timeout
Attempt 3: gemini-2.5-flash          ← second retry
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite 6, TypeScript, React Router v7 |
| **UI** | Tailwind CSS v4, shadcn/ui (Radix UI), Lucide React, Recharts |
| **Backend** | FastAPI, Python 3.11+, Uvicorn |
| **ORM / Migrations** | SQLAlchemy 2.x, Alembic |
| **Database** | PostgreSQL (hosted on Supabase) |
| **AI / LLM** | Google Gemini API (`gemini-3-flash-preview`, fallback `gemini-2.5-flash`) |
| **Auth** | Clerk (JWT / RS256, JWKS with key rotation) |
| **Analytics** | PostHog |
| **HTTP Client** | httpx (async) |
| **PDF Parsing** | pdfplumber |
| **Hosting** | Vercel (frontend), Render (backend) |

---

## Project Structure

```
AI Learning Path Generator/
├── backend/
│   ├── core/               # Clerk JWT verification, rate limiting
│   ├── db/                 # SQLAlchemy engine + session factory
│   ├── migrations/         # Alembic migration versions
│   ├── models/             # SQLAlchemy ORM models
│   ├── mcp_server/         # AI Mentor in-process tool registry
│   │   ├── tools.py        # 5 tool functions + build_user_context()
│   │   └── registry.py     # Gemini declarations + dispatch table
│   ├── routers/            # FastAPI route handlers (HTTP concerns only)
│   │   ├── chat.py         # POST /chat — AI Mentor endpoint
│   │   ├── recommend.py    # GET /recommend
│   │   ├── progress.py     # GET /progress/*
│   │   ├── quiz.py         # Quiz generation + scoring
│   │   ├── github_auth.py  # GitHub OAuth flow
│   │   └── ...
│   ├── services/           # Business logic
│   │   ├── learning_priority_service.py  # Recommendation engine
│   │   ├── skill_graph_service.py        # Graph traversal
│   │   ├── quiz_generation_service.py    # Gemini quiz generation
│   │   ├── quiz_service.py               # Elo scoring + confidence
│   │   ├── github_skill_extractor.py     # GitHub → SkillWeights
│   │   ├── resume_parser.py              # PDF → skill matching
│   │   ├── skill_synthesizer.py          # Merge all skill sources
│   │   └── xp_level_service.py           # XP award + levelling
│   ├── scripts/            # One-off data scripts (ingestion, seeding)
│   ├── main.py             # FastAPI application entry point
│   └── requirements.txt
│
├── src/
│   ├── app/
│   │   ├── components/     # Shared UI (AppSidebar, AppNavbar, OnboardingWizard …)
│   │   ├── pages/          # Route-level page components
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── RoadmapDetailPage.tsx
│   │   │   ├── CourseDetailPage.tsx
│   │   │   ├── QuizPage.tsx
│   │   │   ├── AIMentorPage.tsx
│   │   │   └── MyProfilePage.tsx
│   │   └── hooks/          # useProgress, useRecommendation
│   ├── services/           # Typed API call wrappers per domain
│   ├── components/         # Dashboard-specific cards and charts
│   └── lib/                # xpUtils, roadmapUtils, Supabase client
│
└── docs/CODEMAPS/          # AI-optimised architecture maps
```

---

## Setup Instructions

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- A PostgreSQL database (Supabase free tier works)
- A [Clerk](https://clerk.com) account
- A [Google Gemini API](https://aistudio.google.com) key
- A GitHub OAuth App (for skill extraction)

---

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create `backend/.env` (see [Environment Variables](#environment-variables) below), then run migrations:

```bash
alembic upgrade head
```

Start the server:

```bash
uvicorn main:app --reload --port 8000
```

---

### Frontend Setup

```bash
# From the project root
npm install
```

Create `.env` in the project root (see [Environment Variables](#environment-variables) below), then start the dev server:

```bash
npm run dev
```

The frontend is available at `http://localhost:5173`.

---

## Environment Variables

### Backend (`backend/.env`)

```env
# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Clerk auth
CLERK_JWKS_URL=https://<your-clerk-instance>.clerk.accounts.dev/.well-known/jwks.json
# CLERK_JWT_AUDIENCE=   # only needed if your Clerk instance uses audience claims

# AI
GEMINI_API_KEY=your_gemini_api_key
# GEMINI_CHAT_MODEL=gemini-3-flash-preview      # default
# GEMINI_FALLBACK_MODEL=gemini-2.5-flash        # default

# GitHub OAuth
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret
GITHUB_REDIRECT_URI=http://localhost:8000/github/callback

# Frontend URL (used for OAuth redirect after GitHub callback)
FRONTEND_URL=http://localhost:5173
```

### Frontend (`.env` at project root)

```env
VITE_BACKEND_URL=http://localhost:8000
VITE_CLERK_PUBLISHABLE_KEY=pk_test_...
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_POSTHOG_KEY=phc_...         # optional — analytics
```

---

## How the AI Mentor Works

### 1. Context Pre-Loading

Before every Gemini call, the backend runs `build_user_context(user_id)` — a single DB session that collects:

- Current XP and named level (Novice → Grandmaster)
- Active roadmap, inferred from the user's most recent learning event
- Next recommended course and alternatives in that roadmap
- Top 5 skills ranked by proficiency
- GitHub connection status

This block is appended to the Gemini system prompt so the model can answer questions like "What should I study today?" without any tool-call overhead.

### 2. Gemini Function Calling

For deeper queries, the model can call any of the five MCP tools. The backend runs a function-calling loop (up to 5 rounds per request):

```
User message
  → Gemini (sees context + tool declarations)
  → functionCall {name, args}
  → tool execution (DB query)
  → functionResponse {result}
  → Gemini composes final reply
  → text response → frontend
```

### 3. Security

The authenticated user's ID is always injected server-side into tool arguments — the model cannot query another user's data, even if prompted to attempt it.

### 4. Model Fallback

The `/chat` endpoint retries on `503 UNAVAILABLE` or `httpx.TimeoutException`, cycling through the model chain and logging every fallback for observability.

---

## Future Improvements

- **Streaming responses** — server-sent events via Gemini's `:streamGenerateContent` endpoint for real-time mentor replies
- **Conversation history** — persist chat sessions to the database for multi-turn memory across visits
- **Spaced repetition** — schedule quiz retakes based on Elo decay over time
- **Peer benchmarking** — anonymised skill comparison against users at the same level
- **Custom roadmaps** — allow users to import or create roadmaps beyond the roadmap.sh set
- **Mobile app** — React Native client reusing the existing FastAPI backend
- **Notification system** — alerts when prerequisites are completed and new courses unlock

---

## License

MIT License
