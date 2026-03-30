<!-- Generated: 2026-03-30 | Session: dynamic-roadmap prerequisites, course lock reasons, user level awareness -->

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
Each course includes (a) a `reason` caption describing state, (b) `prerequisites: [{id, title, completed}]` — built from in-memory prerequisite data, cross-roadmap IDs skipped

**Skip/unskip:** Frontend calls `skipCourse()` → validates confidence + prerequisite completion + no duplicate completion → `POST /events {event_type: course_skipped, course_id}` → emits Event. Unskip is `DELETE /events/skip/{course_id}`.

**Quiz loop:** `quiz_generation_service` calls Gemini API → stores `SkillQuiz` → user submits → `quiz_service.evaluate_quiz_attempt()` scores answers → calls `skill_profile_service.update_skill_profile_from_quiz()` → emits `course_completed` Event.

**Elo updates:** Occur inside `routers/learning_path.py` (`get_adaptive_skill_score`) and `routers/events.py` (trust_score adjustments on completion/failure).

## Cold-Start UX Pattern

**Problem:** Render backend cold-starts delay API responses 5–15+ seconds, creating poor perceived performance.

**Solution:** Staged loading state with skeleton screens + progressive messaging:
1. **Skeleton-only phase** (<3s): Display layout skeleton (RoadmapDetailSkeleton, RoadmapCatalogSkeleton, etc.) with no messaging
2. **Server wake-up phase** (5–14s): Append "Waking up our AI servers..." (fades in via `animate-fade-in`)
3. **Data prep phase** (15s+): Show "Preparing your learning paths..."

**Implementation:**
- `DataLoadingState` wrapper component measures elapsed time and conditionally renders messages
- Page components (RoadmapDetailPage, RoadmapCatalogPage, CourseDetailPage, ResourceViewerPage) wrap their content in `<DataLoadingState><[PageName]Skeleton/></DataLoadingState>` during loading
- `fade-in` Tailwind animation defined in `src/styles/tailwind.css` (opacity + translateY, 0.4s ease-out)

**User experience:** Skeleton reassures users something is happening; staged messages explain temporary delay without false urgency.

## XP & Level Display System

**Purpose:** Make ELO ratings (backend 800–2000 scale) intuitive for end-users via a 6-level XP system.

**Conversion Formula:**
- ELO → XP: `xp = Math.min(1000, Math.max(0, elo - 1000))` (base ELO 1000 = 0 XP; clamped to max 1000)
- Level thresholds: `[0, 150, 400, 650, 850, 1000]` (indices = level - 1)
  - Level 1: 0–150 XP (ELO 1000–1150) = Novice
  - Level 2: 150–400 XP (ELO 1150–1400) = Apprentice
  - Level 3: 400–650 XP (ELO 1400–1650) = Practitioner
  - Level 4: 650–850 XP (ELO 1650–1850) = Proficient
  - Level 5: 850–1000 XP (ELO 1850–2000) = Expert
  - Level 6: 1000 XP (ELO 2000, max) = Master

**Components:**
- `XPLevelBadge` — Renders user skill ELO as Level badge (circle) + XP counter + progress bar with monospace font + glow
- `CourseDifficultyBadge` — Inline badge showing course difficulty as "Lvl N — Label"; accepts `userLevel?: number` prop to show "Requires Level N" only when user hasn't met requirement (otherwise neutral "Level Requirement: N — Label")
- `xpUtils.ts` — Shared conversion logic: `eloToLevel()`, `eloToXP()`, `getCourseDifficultyInfo()`

**Usage:** Dashboard Skill Radar Chart, MyProfilePage, RoadmapDetailPage, CourseDetailPage all display XP/levels to users.

## Lock Reason Callout Pattern

**When a course is locked**, RoadmapDetailPage renders:
1. **Amber callout** — "This course is locked" with explanation
2. **Full prerequisite list** — Each prerequisite shown with `{title, completed: boolean}` from API `prerequisites[]` field
   - Completed: green checkmark + title
   - Pending: gray "Start Learning →" link to course
3. **Difficulty badge** — `CourseDifficultyBadge` with user's `userLevel` prop (shows "Requires Level N" only if user level is the blocker)

**Flow:** Frontend calls `getDynamicRoadmapStatus()` → receives `DynamicCourseNode` with `prerequisites` array → for locked cards, renders them sorted by status order.
