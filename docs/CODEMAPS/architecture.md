<!-- Generated: 2026-04-01 | Sprint: 5 (AI Mentor feature) | Gemini function-calling chat loop, MCP tools, /chat router -->

# Architecture Overview

LearnPathAI is a full-stack adaptive learning platform. Users connect GitHub and upload a resume; the backend synthesizes skill proficiency into an XP + Level profile. A dynamic roadmap engine surfaces a 5-state course map (locked | unlocked | fast_tracked | skippable | completed) driven by level-based prerequisites. Users study resources, take AI-generated quizzes, earn XP/levels, skip courses, and progression drives the next recommendation.

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
          │   └ HTTP concerns only; return xp/level not elo
          ├ Services (backend/services/*)
          │   ├ learning_priority_service   → recommendation engine
          │   ├ skill_graph_service         → graph traversal / unlock logic
          │   ├ xp_level_service            → XP awards + level derivation
          │   ├ course_level_service        → compute_required_level(depth)
          │   ├ quiz_generation_service     → Gemini API quiz gen
          │   ├ skill_synthesizer           → merge GitHub + resume weights
          │   ├ github_skill_extractor      → GitHub API → SkillWeights
          │   ├ resume_parser               → PDF → SkillWeights
          │   └ skill_profile_service       → cold-start + profile CRUD
          └ Models (backend/models/*)
                ↓
          PostgreSQL (Supabase) via SQLAlchemy
```

## Progression System: XP + Levels

**Level Range:** 1–6 (integer). Earned via course completion and quiz attempts.

**XP Thresholds:**
- Level 1: 0 XP | Level 2: 150 XP | Level 3: 400 XP | Level 4: 650 XP | Level 5: 850 XP | Level 6: 1000 XP

**XP Award Formula:**
- **Completion:** `depth * 20 + 10` (min 10 XP)
- **Quiz:** Full XP if ≥80%, half XP if ≥50%, 0 if <50%
- Awards apply to both `User.total_xp` (global) and `UserSkill.xp` (roadmap-scoped)

**Course Required Level:** Integer 1–6 computed via `course_level_service.compute_required_level(topological_depth)`. Level filter: user unlocks courses where `required_level ≤ user_level + 1`.

## Key Data Flows

**Skill ingestion:** GitHub OAuth → `github_skill_extractor` → `SkillWeight` rows | Resume upload → `resume_parser` → `SkillWeight` rows → `skill_synthesizer` → `SkillProfile` rows.

**Progression loop:** User completes course → `award_xp_for_completion()` increments `User.total_xp` + `User.current_level` + `UserSkill.xp` + `UserSkill.level` → `POST /events {event_type: course_completed}` → next recommendation fires.

**Dynamic roadmap status:** `compute_dynamic_roadmap()` fetches 4 data sets in parallel — (Q1) all courses; (Q2) satisfied IDs (completed + skipped events); (Q3) prerequisites; (Q4) skill profiles — then applies 5-state resolution:
1. **completed** — if course_id in satisfied_ids
2. **skippable** — if all prereqs satisfied AND confidence ≥ 0.75
3. **fast_tracked** — if all prereqs satisfied AND confidence ≥ 0.50
4. **unlocked** — if all prereqs satisfied
5. **locked** — otherwise (+ reason explaining blocker)

Each course includes `prerequisites: [{id, title, completed}]` built from in-memory prerequisite data.

**Skip/unskip:** Frontend calls `skipCourse()` → validates confidence + prerequisites → `POST /events {event_type: course_skipped}` → reverses via `DELETE /events/skip/{courseId}`.

**Quiz loop:** `quiz_generation_service` → Gemini → `SkillQuiz` row → user submits → `quiz_service.evaluate_quiz_attempt()` scores → `award_xp_for_quiz()` updates levels → `POST /events {event_type: course_completed}`.

## Onboarding UX Pattern (Sprint 3)

**Problem:** New users without skills or GitHub connection need guidance on how to start.

**Solution:** Conditional onboarding wizard shown only to new users:
- **Condition:** `onboarding_completed = False` AND `skills.length = 0` AND `!githubConnected`
- **Display:** DashboardPage renders `<OnboardingWizard />` card at top (dismissible)
- **Steps:** (1) Import skills (GitHub or resume), (2) Pick a learning path, (3) Start learning
- **Completion:** User dismisses card OR completes all steps → `POST /users/me/onboarding/complete` → `users.onboarding_completed = True`
- **Implementation:** `src/app/components/OnboardingWizard.tsx` + DashboardPage state: `getCurrentUser()` fetches flag, `handleDismissOnboarding()` calls backend

## Cold-Start UX Pattern

**Problem:** Render backend cold-starts delay API responses 5–15+ seconds.

**Solution:** Staged loading with skeleton screens + progressive messaging:
1. **Skeleton phase** (<3s): Layout skeleton only
2. **Server wake-up** (5–14s): "Waking up our AI servers..." fades in
3. **Data prep** (15s+): "Preparing your learning paths..."

**Implementation:** `DataLoadingState` wrapper measures elapsed time; pages wrap content in `<DataLoadingState><[Page]Skeleton/></DataLoadingState>`. `fade-in` animation in `src/styles/tailwind.css`.

## User Level Display

**XPLevelBadge:** Shows user's current level (1–6) + XP progress bar + monospace font + glow effect. Backend returns `user_xp` + `user_level` directly (no conversion).

**CourseDifficultyBadge:** Shows course required_level (1–6) as "Lvl N — Label" (e.g., "Lvl 3 — Practitioner"). Optional `userLevel` prop shows "Requires Level N" only if user hasn't met requirement.

## Lock Reason Callout Pattern

**When a course is locked**, RoadmapDetailPage renders:
1. **Amber callout** — "This course is locked" + explanation
2. **Full prerequisite list** — Each `{title, completed}` from API `prerequisites[]` with checkmark or "Start Learning →" link
3. **Difficulty badge** — `CourseDifficultyBadge` with `userLevel` prop

**Flow:** Frontend calls `getDynamicRoadmapStatus()` → receives `DynamicCourseNode[]` with `prerequisites` array → renders locked prerequisites sorted by completion status.

## Sprint 2 Updates: UI Enhancements & Progress Tracking

**ErrorBoundary (NEW):** `src/app/components/ErrorBoundary.tsx` — React class component wraps `AppLayout` in `src/app/App.tsx`. Catches unhandled exceptions and renders recovery UI with "Reload page" button.

**Toast System (NEW):** `Toaster` mounted in `src/main.tsx` with position "bottom-right" and richColors enabled. Toast notifications now wired to:
- `RoadmapDetailPage`: skip/unskip success/error messages
- `MyProfilePage`: all alerts (resume upload, GitHub sync, skill rebuild)
- `QuizPage`: submit error messages

**RoadmapDetailPage Enhancements (NEW):**
- **Search input** — case-insensitive `title` filtering
- **Status filter chips** — all | unlocked | completed | locked
- **Progress summary bar** — "X/Y completed, N unlocked, N locked"

**AppSidebar XP Badge (NEW):** Compact XP/Level display above Logout button. Fetches `getUserProfile()` on mount. Shows level circle + label + XP count + progress bar with theme colors from `xpUtils.LEVEL_COLORS`.

**useProgress Hook (UPDATED):** Now fires server-side events (`resource_viewed`, `resource_completed`) on mark calls (write-through pattern). Events persisted to `POST /events` with fire-and-forget semantics.

**API Resilience (UPDATED):** `src/services/api.ts` `fetchWithAuth()` now retries 3x on 502/503/504 with exponential backoff (600ms, 1200ms, 2400ms). Handles Render cold starts transparently.

**Quiz Result Screen (UPDATED):** Displays `+XP badge` showing `xp_awarded`. Shows level-up notification if `leveled_up` field is true. Backend `POST /quiz/{skill_id}/submit` now returns `xp_awarded`, `total_xp`, `current_level`, `leveled_up`.

**Event Tracking (UPDATED):** `backend/routers/events.py` now accepts `resource_completed` event type (lines 21, 106). `useProgress` hook posts this on resource mark-complete.

## Sprint 3 Updates: Onboarding & Improved Empty States

**OnboardingWizard (NEW):** `src/app/components/OnboardingWizard.tsx` — Conditional card shown to new users (no skills, no GitHub, not dismissed). 3 steps: import skills, pick roadmap, start learning. Dismissal triggers `POST /users/me/onboarding/complete` to set `users.onboarding_completed = True`.

**DashboardPage Integration (UPDATED):** Fetches `getCurrentUser()` on mount to read `onboarding_completed` flag. Computes `isNewUser` predicate and conditionally renders wizard above hero section. Handles wizard dismissal via `handleDismissOnboarding()`.

**Empty State Improvements (UPDATED):**
- **LearningInsightsCard:** Empty state shows "No activity yet" with actionable "Browse Paths →" link
- **SkillRadarChart:** Distinguishes zero-skills users ("Connect your skills → /profile") from low-roadmap users ("Start a path → /roadmaps")

**Backend Onboarding Endpoint (NEW):** `POST /users/me/onboarding/complete` in `backend/routers/users.py` sets `users.onboarding_completed = True`. Also added `onboarding_completed` field to `GET /users/me` response.

**Migration (NEW):** `backend/migrations/versions/20260331_add_onboarding_completed.py` adds `users.onboarding_completed` column (BOOLEAN, default FALSE). Backfills existing users to FALSE.

## Sprint 5 Updates: AI Mentor (Gemini Function-Calling)

**AIMentorPage (NEW):** `/ai-mentor` route displays chat UI (message bubbles, typing indicator, textarea). Sends user messages to `POST /chat` via `sendChatMessage()`. Renders streaming replies with auto-scroll.

**Chat Endpoint (NEW):** `backend/routers/chat.py` — `POST /chat` accepts `{message: string}` → runs Gemini function-calling loop (max 5 rounds, 60s timeout). Sends Gemini `TOOL_DECLARATIONS` (5 tools) in every request; model calls tools, backend executes via `TOOL_REGISTRY`, feeds results back; loop continues until no tool calls remain. Returns `ChatResponse{reply: string}`.

**MCP Tools (NEW):** `backend/mcp_server/tools.py` — 5 functions that fetch real data for Gemini:
- `get_user_profile()` → `{email, elo, xp, level, github_status, skills[]}`
- `get_user_progress()` → `{total_completed, roadmaps[{id, total, completed, progress%}]}`
- `get_next_course(user_id, roadmap_id)` → calls `get_recommended_start_courses_batched()`
- `get_roadmap_courses(roadmap_id)` → list courses with `difficulty_level`, `required_level`
- `get_skill_graph(roadmap_id, user_id?)` → skill edges ± user completion status

**Tool Registry (NEW):** `backend/mcp_server/registry.py` — `TOOL_DECLARATIONS` (Gemini JSON schema), `USER_ID_TOOLS` (set of tools that require auth override), `TOOL_REGISTRY` (dispatch table). Router always replaces tool `user_id` args with authenticated user's ID for security.

**Sidebar Integration (UPDATED):** Added "AI Mentor" nav item (MessageSquare icon) between "Learning Paths" and "My Profile".

**System Prompt:** Instructs Gemini to use tools to fetch real data before answering; discourages hallucinated stats.

## Sprint 4 Updates: Quiz Result Split & Learning Progress Dashboard

**QuizPage Result Screen (SPLIT):** Quiz result screen now conditionally renders two distinct experiences:
- **Passed (≥80%):** Green celebration card with "Course Completed" headline, XP + level-up badges, CTAs: "View Learning Path →" (`/roadmap/{id}`), "Go to Dashboard", and "Retake Quiz"
- **Failed (<80%):** Original score card with score percentage, mastery stats, "Retake Quiz" and "Back to Course" CTAs; shows review recommendations

**QuizPage Loading (NEW):** `DataLoadingState` wrapper + `QuizSkeleton` component while Gemini generates questions. Skeleton mirrors actual question card: breadcrumb → title + counter → progress bar → 4-option question card.

**CourseDetailPage (UPDATED):**
- Replaced raw `fetch()` + manual auth headers with `fetchWithAuth()` (adds retry on 502/503/504 with exponential backoff)
- Added course description rendering below title
- Added "X/Y done" progress bar in page header using `getCourseProgress()` hook

**MyProfilePage "Learning Progress" Card (NEW):** `src/app/pages/MyProfilePage.tsx` section 2.
- **Stats row:** 4 tiles (Level, Total XP, Courses Completed, Active Paths)
- **XP progress bar:** Shows current XP, next-level threshold, percentage to next level
- **Per-roadmap mini bars:** Top 4 active roadmaps by progress; stacked mobile view
- Data: `getUserProfile()` + `getUserSkills()` + `getLevelFromXP()` + theme colors from `LEVEL_COLORS` + labels from `LEVEL_LABELS`

**Deleted:** `src/app/pages/ProfilePage.tsx` (was dead code; functionality moved to `MyProfilePage`)
