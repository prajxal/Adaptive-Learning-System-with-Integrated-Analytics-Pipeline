<!-- Generated: 2026-03-26 | Session: dynamic-roadmap + reason-metadata + bug-fixes -->

# Frontend Codemap

## Entry Point

`src/main.tsx` — Renders `<App />` wrapped in `ClerkProvider`, `PostHogProvider`, `PostHogErrorBoundary`, plus `TokenSynchronizer` and `PostHogIdentifier`.

## App Shell

`src/app/App.tsx` — `BrowserRouter` with route definitions. Protected routes render inside `AppLayout` (sidebar + navbar). Unauthenticated users redirect to `/signin`. `/progress` redirects to `/dashboard`.

## Routes

| Path | Component | File |
|------|-----------|------|
| `/` | LandingPage | `src/app/pages/LandingPage.tsx` |
| `/signin` | Login | `src/app/pages/Login.tsx` |
| `/signup` | Signup | `src/app/pages/Signup.tsx` |
| `/dashboard` | DashboardPage | `src/app/pages/DashboardPage.tsx` |
| `/roadmaps` | RoadmapCatalogPage | `src/app/pages/RoadmapCatalogPage.tsx` |
| `/roadmap/:roadmapId` | RoadmapDetailPage | `src/app/pages/RoadmapDetailPage.tsx` |
| `/course/:courseId` | CourseDetailPage | `src/app/pages/CourseDetailPage.tsx` |
| `/course/:courseId/resource/:resourceId` | ResourceViewerPage | `src/app/pages/ResourceViewerPage.tsx` |
| `/course/:courseId/quiz` | QuizPage | `src/app/pages/QuizPage.tsx` |
| `/profile` | MyProfilePage | `src/app/pages/MyProfilePage.tsx` |
| `/progress` | → redirect `/dashboard` | (removed) |

**Unused page files** (not mounted in routes): `ProfilePage.tsx`, `CourseCatalogPage.tsx`, `RoadmapPage.tsx`, `TopicDetailPage.tsx`

## Shared Components

| Component | File | Notes |
|-----------|------|-------|
| AppNavbar | `src/app/components/AppNavbar.tsx` | |
| AppSidebar | `src/app/components/AppSidebar.tsx` | menu: Dashboard, Learning Paths, My Profile |
| AppBreadcrumb | `src/app/components/AppBreadcrumb.tsx` | wraps shadcn Breadcrumb; accepts `segments: {label, href?}[]` |
| RecommendationPanel | `src/app/components/RecommendationPanel.tsx` | ELO badge + recommended/alternative starts + explore paths |
| RoadmapNode | `src/app/components/RoadmapNode.tsx` | **Updated**: `NodeStatus` now includes `skippable`, `fast_tracked`; accepts `isSkipLoading`, `onSkip`, `onFastTrack`, `reason` props |
| RoadmapContainer | `src/app/components/RoadmapContainer.tsx` | forwards new skip/fast-track props through to `RoadmapNode` |
| LoadingSkeleton | `src/app/components/LoadingSkeleton.tsx` | |
| LemonButton/Card/Input/Modal/ProgressBar | `src/app/components/Lemon*.tsx` | |
| shadcn/ui primitives | `src/app/components/ui/*.tsx` | includes breadcrumb, chart, tabs, badge, etc. |

## Page Details

### RoadmapDetailPage
Migrated to single `getDynamicRoadmapStatus()` call (replaces 3 prior API calls). Renders 5-state course map with:
- Per-course status badge (Mastered, Skip Available, Fast Track, Unlocked, Locked)
- Reason caption explaining state (e.g., "Skipped — high confidence (85%)", "Locked — 2 prerequisites remaining")
- Skip/unskip buttons for `skippable` courses (with loading + error UI per course)
- Recommendation banner showing next suggested course + alternatives
- Breadcrumb: Home → Learning Paths → {roadmapId}

### CourseDetailPage
Migrated from old `/status` to `getDynamicRoadmapStatus()`.

### Other Pages
| Page | Breadcrumb Path |
|------|----------------|
| RoadmapCatalogPage | Home → Learning Paths |
| ResourceViewerPage | Home → {roadmap} → {resource.title} (sidebar) |
| QuizPage | Home → {roadmap} → {course title} → Quiz |

## Dashboard Components (`src/components/dashboard/`)

| Component | Props | Purpose |
|-----------|-------|---------|
| LearningInsightsCard | `skills[], githubConnected, recommendedCourse?, loading` | 4-panel analytics: Descriptive / Diagnostic / Predictive / Prescriptive |
| SkillRadarChart | `skills[], loading` | recharts RadarChart — dynamic axes (top 8 roadmaps by Elo, normalized 0–100) |
| GithubInsightsCard | `githubAnalysis, loading` | Developer Profile Insights — language pills (LANG_COLORS map), suggested learning focus (LANGUAGE_TO_FOCUS lookup), activity signal strength bar (Strong/Moderate/Getting Started). **Used in MyProfilePage, not Dashboard.** |

**Deleted:** `SkillSnapshotCard.tsx`, `SkillProfileCard.tsx`

## Dashboard Page Layout (`DashboardPage.tsx`)

Data fetched: `getUserSkills()`, `getRoadmaps()`, `getGithubStatus()` (connected boolean only), `/recommend/recommend?current_roadmap_id=X` (after skills load).

1. **Continue Learning hero** — resumes last-accessed course (or "Start journey" CTA); skip suggestion messaging for recommended courses with high confidence
2. **Recommended Next Step** — `recommendation.next_in_current_roadmap[0]` + alternatives `[1-2]`
3. **Learning Paths** section:
   - *In Progress* — `skills where progress_percent > 0 && < 100`
   - *Explore* — roadmaps not in `skills[]` + `suggested_new_roadmaps` from recommendation
4. **Learning Insights** + **Skill Radar Chart** — side-by-side 2-col grid (lg), stacked mobile

## My Profile Page Layout (`MyProfilePage.tsx`)

Route: `/profile`. Data fetched: `getGithubStatus()`, `getGithubAnalysis()`, `checkResumeStatus()`.

1. **Account** — Clerk `useUser()` avatar, display name, email
2. **Connected Accounts** — GitHub connect/sync/disconnect; polls `sync_status` every 5 s when syncing
3. **Resume** — PDF upload + status indicator (`checkResumeStatus()` on load + after upload)
4. **Developer Profile** — `GithubInsightsCard` (language pills, suggested focus, activity signal)
5. **Skill Profile** — Rebuild button → `POST /users/me/skills/rebuild`

OAuth callback (`GET /github/callback`) redirects to `/profile?github=connected`; the page handles the toast.

## API Service Layer

### Core API (`src/services/api.ts`)
Exports `BACKEND_URL`, `getClerkToken()`, `fetchWithAuth()` — used by all other API modules.

### Granular API Modules (`src/services/`)

| Module | File | Backend Endpoints Hit |
|--------|------|-----------------------|
| courseApi | `src/services/courseApi.ts` | `/courses` |
| roadmapApi | `src/services/roadmapApi.ts` | `/roadmaps` — `getRoadmaps()` returns `{id, topic_count}[]` |
| dynamicRoadmapApi | `src/services/dynamicRoadmapApi.ts` | `/skill-graph/{roadmapId}/dynamic-status`, `/events`, `/events/skip/{courseId}` — `getDynamicRoadmapStatus()`, `skipCourse()`, `unskipCourse()` |
| progressApi | `src/services/progressApi.ts` | `/progress/*`, `/progress/all` |
| userApi | `src/services/userApi.ts` | `/users/me/*` — `getUserSkills()`, `getUserProfile()`, `getUserSkillProfile()` |
| githubApi | `src/services/githubApi.ts` | `/github/*` |
| resumeApi | `src/services/resumeApi.ts` | `/resume/*` |

### Page-Level API (`src/app/services/`)

| Module | File |
|--------|------|
| api.ts | `src/app/services/api.ts` — `getRecommendation(roadmapId)`, `getUser()`, `sendEvent()` |
| auth.ts | `src/app/services/auth.ts` — `signup()`, `login()` |
| quizApi.ts | `src/app/services/quizApi.ts` — `getSkillProfile()`, `getQuiz()`, `submitQuizAttempt()` |

## Custom Hooks

| Hook | File | Description |
|------|------|-------------|
| useProgress | `src/app/hooks/useProgress.ts` | localStorage progress tracker; `markResourceComplete`, `markResourceInProgress`, `getResourceProgress`, `getCourseProgress`, `getRoadmapProgress`, `getLastAccessed` |
| useCourses | `src/hooks/useCourses.ts` | Fetches courses from backend |
| useRoadmaps | `src/hooks/useRoadmaps.ts` | Fetches roadmap list via `getRoadmaps()` |
| useUserSkills | `src/hooks/useUserSkills.ts` | Fetches user skills |
| useRecommendation | `src/app/hooks/useRecommendation.ts` | Fetches `/recommend/recommend` (requires roadmapId) |

## Auth Utilities

| File | Purpose |
|------|---------|
| `src/auth/TokenSynchronizer.tsx` | Clerk JWT synchronization |
| `src/auth/PostHogIdentifier.tsx` | PostHog user identification |

## Key Dependencies

- **recharts** 2.15.2 — RadarChart used in SkillRadarChart
- **lucide-react** 0.487.0 — icons
- **react-router-dom** 7.13.0 — routing
- **@clerk/clerk-react** — auth
- **@posthog/react** — analytics
- **shadcn/ui** via radix-ui primitives + tailwind

## Constants

`src/app/constants/routes.ts` — `ROUTES.COURSE(id)`, `ROUTES.ROADMAP(id)`, `ROUTES.DASHBOARD`, `ROUTES.QUIZ(courseId)`, `ROUTES.RESOURCE(courseId, resourceId)`
