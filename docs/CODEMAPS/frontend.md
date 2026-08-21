<!-- Generated: 2026-04-01 | Sprint: 5 (AI Mentor context injection) | /ai-mentor route, AIMentorPage component, sendChatMessage API, AppSidebar nav update -->

# Frontend Codemap

## Entry Point

`src/main.tsx` — Renders `<App />` wrapped in `ClerkProvider`, `PostHogProvider`, `PostHogErrorBoundary`, plus `TokenSynchronizer`, `PostHogIdentifier`, and **`<Toaster position="bottom-right" richColors />`** (NEW: Sonner toast component, no longer using next-themes, hardcoded dark theme).

## App Shell

`src/app/App.tsx` — `BrowserRouter` with route definitions. Protected routes render inside `AppLayout` (sidebar + navbar) **wrapped in `<ErrorBoundary />`** (NEW: catches unhandled exceptions). Unauthenticated users redirect to `/signin`. `/progress` redirects to `/dashboard`.

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
| `/ai-mentor` | AIMentorPage | `src/app/pages/AIMentorPage.tsx` | **NEW (Sprint 5)** |
| `/progress` | → redirect `/dashboard` | (removed) |

**Unused page files:** `CourseCatalogPage.tsx`, `RoadmapPage.tsx`, `TopicDetailPage.tsx` (deleted: `ProfilePage.tsx` — merged into `MyProfilePage`)

## Shared Components

| Component | File | Notes |
|-----------|------|-------|
| **OnboardingWizard** | **`src/app/components/OnboardingWizard.tsx`** | **NEW (Sprint 3):** Onboarding card for new users; 3 steps: import skills, pick roadmap, start learning. Shown when `onboarding_completed = False` AND user has no skills + no GitHub. Dismiss calls `POST /users/me/onboarding/complete` |
| ErrorBoundary | `src/app/components/ErrorBoundary.tsx` | React class component catches unhandled exceptions; renders recovery UI with "Reload page" button |
| AppNavbar | `src/app/components/AppNavbar.tsx` | |
| AppSidebar | `src/app/components/AppSidebar.tsx` | menu: Dashboard, Learning Paths, **AI Mentor** (NEW), My Profile; compact XP/Level badge above Logout (fetches `getUserProfile()` on mount, shows level circle + label + XP count + progress bar) |
| AppBreadcrumb | `src/app/components/AppBreadcrumb.tsx` | wraps shadcn Breadcrumb |
| RecommendationPanel | `src/app/components/RecommendationPanel.tsx` | XP badge + recommended/alternative starts + explore paths |
| RoadmapNode | `src/app/components/RoadmapNode.tsx` | `NodeStatus` includes `skippable`, `fast_tracked`; skip/unskip buttons fire toast notifications |
| RoadmapContainer | `src/app/components/RoadmapContainer.tsx` | forwards skip/fast-track props to `RoadmapNode` |
| DataLoadingState | `src/app/components/DataLoadingState.tsx` | Staged loading messages: skeleton only (<3s), "Waking up..." (5–14s), "Preparing..." (15s+) |
| LoadingSkeleton | `src/app/components/LoadingSkeleton.tsx` | |
| LemonButton/Card/Input/Modal/ProgressBar | `src/app/components/Lemon*.tsx` | |
| shadcn/ui primitives | `src/app/components/ui/*.tsx` | breadcrumb, chart, tabs, badge, etc.; includes `sonner` Toaster |

### Skeleton Screens (`src/app/components/skeletons/`)

| Component | File | Used By |
|-----------|------|---------|
| RoadmapCatalogSkeleton | `src/app/components/skeletons/RoadmapCatalogSkeleton.tsx` | RoadmapCatalogPage |
| RoadmapDetailSkeleton | `src/app/components/skeletons/RoadmapDetailSkeleton.tsx` | RoadmapDetailPage |
| CourseDetailSkeleton | `src/app/components/skeletons/CourseDetailSkeleton.tsx` | CourseDetailPage |
| ResourceViewerSkeleton | `src/app/components/skeletons/ResourceViewerSkeleton.tsx` | ResourceViewerPage |
| **QuizSkeleton** | **`src/app/components/skeletons/QuizSkeleton.tsx`** | **QuizPage (Sprint 4)** — Mirrors quiz question card: breadcrumb → title + counter → progress bar → 4-option question rows |

### Display Badges & Utilities

| Component | File | Purpose |
|-----------|------|---------|
| CourseDifficultyBadge | `src/app/components/CourseDifficultyBadge.tsx` | Renders course `required_level` (1–6) as "Lvl N — Label"; optional `userLevel` prop shows "Requires Level N" only when user hasn't met requirement |
| XPLevelBadge | `src/app/components/XPLevelBadge.tsx` | Displays user `xp` (0–1000) + `level` (1–6) badge with progress bar, monospace font, glow. Props: `xp`, `level` |

## Page Details

### RoadmapDetailPage
Fetches user `total_xp` + `current_level` from `getUserProfile()`. Calls `getDynamicRoadmapStatus()` once. Renders 5-state course map with:
- Per-course status badge (Mastered, Skip Available, Fast Track, Unlocked, Locked)
- Reason caption + full prerequisite list (`prerequisites[]` from API)
- For locked: amber callout + prerequisite list + `CourseDifficultyBadge` with `userLevel` prop
- Skip/unskip buttons for `skippable` courses; fires toast on success/error
- **NEW:** Search input (case-insensitive title filtering)
- **NEW:** Status filter chips (all | unlocked | completed | locked)
- **NEW:** Progress summary bar ("X/Y completed, N unlocked, N locked")
- Recommendation banner
- **Cold-start UX**: Wraps in `<DataLoadingState><RoadmapDetailSkeleton/></DataLoadingState>`

### RoadmapCatalogPage
- **Cold-start UX**: `<DataLoadingState><RoadmapCatalogSkeleton/></DataLoadingState>`

### CourseDetailPage
- Fetches `getDynamicRoadmapStatus()` + course data
- **Cold-start UX**: `<DataLoadingState><CourseDetailSkeleton/></DataLoadingState>`

### Other Pages
| Page | Cold-Start UX |
|------|---------------|
| ResourceViewerPage | `<DataLoadingState><ResourceViewerSkeleton/></DataLoadingState>` |
| **QuizPage** | **`<DataLoadingState><QuizSkeleton/></DataLoadingState>` (NEW Sprint 4)** |

## Dashboard Components (`src/components/dashboard/`)

| Component | Purpose |
|-----------|---------|
| **LearningInsightsCard** | **Updated (Sprint 3):** 4-panel analytics (Descriptive / Diagnostic / Predictive / Prescriptive); improved empty states with actionable Link buttons (→ /roadmaps, → /roadmaps for quizzes) |
| **SkillRadarChart** | **Updated (Sprint 3):** recharts RadarChart — dynamic axes (top 8 roadmaps by level, normalized 0–100); empty state distinguishes zero-skills users (→ /profile) from low-roadmap users (→ /roadmaps) |
| GithubInsightsCard | Developer Profile Insights — language pills, suggested focus, activity signal |

**Deleted:** `SkillSnapshotCard.tsx`, `SkillProfileCard.tsx`

## Dashboard Page Layout (`DashboardPage.tsx`)

Data fetched: `getCurrentUser()` (onboarding_completed flag), `getUserSkills()` (with `xp`, `level`), `getRoadmaps()`, `getGithubStatus()`, `/recommend/recommend?current_roadmap_id=X`.

**New users** (`onboarding_completed = False` AND no skills AND no GitHub):
- **OnboardingWizard card** (dismissible) — 3-step wizard: import skills, pick roadmap, start learning

All users:
1. **Continue Learning hero** — resumes last-accessed course
2. **Recommended Next Step** — `recommendation.next_in_current_roadmap[0]` + alternatives (context-aware CTAs)
3. **Learning Paths** section — In Progress / Explore (improved empty states with actionable Links)
4. **Learning Insights** + **Skill Radar Chart** — 2-col grid (lg), stacked mobile (improved empty states distinguish zero-skills vs low-roadmap users)

## My Profile Page Layout (`MyProfilePage.tsx`)

Route: `/profile`. Data: `getGithubStatus()`, `getGithubAnalysis()`, `checkResumeStatus()`, `getUserProfile()`, `getUserSkills()`.

1. **Account** — Clerk `useUser()`
2. **Learning Progress** — **NEW (Sprint 4):** 4 stat tiles (Level, Total XP, Courses Completed, Active Paths); XP progress bar with next-level info; per-roadmap mini bars (top 4)
3. **Connected Accounts** — GitHub connect/sync/disconnect
4. **Resume** — PDF upload + status
5. **Developer Profile** — `GithubInsightsCard`
6. **Skill Profile** — Rebuild button

## API Service Layer

### Core API (`src/services/api.ts`)
Exports `BACKEND_URL`, `getClerkToken()`, `fetchWithAuth()`. **UPDATED:** `fetchWithAuth()` now retries 3x on 502/503/504 with exponential backoff (600ms, 1200ms, 2400ms). Handles Render cold starts transparently.

### Granular API Modules (`src/services/`)

| Module | File | Returns |
|--------|------|---------|
| **chatApi** | **`src/services/chatApi.ts`** | **`sendChatMessage(message): Promise<string>` → POST /chat via fetchWithAuth (NEW Sprint 5)** |
| courseApi | `src/services/courseApi.ts` | `{id, title, required_level}[]` (not `difficulty_level`) |
| roadmapApi | `src/services/roadmapApi.ts` | `{id, topic_count}[]` |
| dynamicRoadmapApi | `src/services/dynamicRoadmapApi.ts` | `DynamicCourseNode[]` with `prerequisites: CoursePrerequisiteRef[]` |
| progressApi | `src/services/progressApi.ts` | `{xp, level}` per roadmap |
| userApi | `src/services/userApi.ts` | **NEW (Sprint 3):** `getCurrentUser()` → `{onboarding_completed, ...}`, `completeOnboarding()` → `void`; plus `getUserProfile()`, `getUserSkills()` |
| githubApi | `src/services/githubApi.ts` | GitHub connection status |
| resumeApi | `src/services/resumeApi.ts` | Resume upload status |

### Page-Level API (`src/app/services/`)

| Module | File |
|--------|------|
| api.ts | `getRecommendation()`, `getUser()`, `sendEvent()` |
| auth.ts | `signup()`, `login()` |
| quizApi.ts | `getQuiz()`, `submitQuizAttempt()` |

## Custom Hooks

| Hook | File | Purpose |
|------|------|---------|
| useProgress | `src/app/hooks/useProgress.ts` | localStorage progress tracker; **UPDATED:** `markResourceComplete()` + `markResourceInProgress()` now fire server-side events (`resource_completed`, `resource_viewed`) via `POST /events` (write-through pattern) |
| useCourses | `src/hooks/useCourses.ts` | Fetches courses |
| useRoadmaps | `src/hooks/useRoadmaps.ts` | Fetches roadmap list |
| useUserSkills | `src/hooks/useUserSkills.ts` | Fetches user skills with `xp`, `level` |
| useRecommendation | `src/app/hooks/useRecommendation.ts` | Fetches `/recommend/recommend` |

## Utility Modules

| Module | Exports | Purpose |
|--------|---------|---------|
| xpUtils | `LEVEL_THRESHOLDS`, `LEVEL_LABELS`, `LEVEL_COLORS`, `getLevelFromXP()`, `xpToLevel()`, `getCourseDifficultyInfo()` | XP (0–1000) + Level (1–6) logic; **Removed:** `eloToXP()`, `eloToLevel()` (backend now returns XP directly) |
| roadmapUtils | `sortDynamicCourses(courses, recommendedId)` | Sorts courses by difficulty → recommended → status order |

## Auth Utilities

| File | Purpose |
|------|---------|
| `src/auth/TokenSynchronizer.tsx` | Clerk JWT sync |
| `src/auth/PostHogIdentifier.tsx` | PostHog identification |

## Styling & Animations

- **Tailwind CSS** — `src/styles/tailwind.css` defines `fade-in` keyframe used by `DataLoadingState`
- **animate-fade-in** — applied at ≥5s elapsed

## Testing

- **vitest** — unit testing (zero-dependency, node environment)
- Test files: `src/lib/__tests__/xpUtils.test.ts` (40 tests), `src/lib/__tests__/roadmapUtils.test.ts` (10 tests)
- Config: `vitest.config.ts` (minimal)

## AI Mentor Page (`AIMentorPage.tsx`) **NEW (Sprint 5)**

Route: `/ai-mentor`. Displays chat interface:
- **Header:** MessageSquare icon + "AI Mentor" title + "Powered by your real learning data" subtitle
- **Message list:** Scrollable message bubbles (user: right-aligned indigo, assistant: left-aligned dark)
- **Typing indicator:** 3 animated dots while assistant is composing
- **Input area:** Textarea (Enter to send, Shift+Enter for newline) + Send button
- **Data:** Calls `sendChatMessage(text)` via `src/services/chatApi.ts` → `POST /chat` with Clerk auth
- **Behavior:** Maintains conversation state; appends user message → loading state → fetches reply → appends assistant message; auto-scrolls to bottom

## Key Updates (Sprint 4)

**QuizPage Result Screen:**
- Passed: Green celebration card → "View Learning Path →" + "Go to Dashboard" + "Retake Quiz"
- Failed: Score card → "Retake Quiz" + "Back to Course"
- XP + level-up badges displayed on success

**CourseDetailPage:**
- Uses `fetchWithAuth()` with retry on 502/503/504
- Shows course description
- Progress bar header with `getCourseProgress()` hook

**MyProfilePage:**
- Added "Learning Progress" section (2nd card)
- Stats: Level, Total XP, Courses Done, Active Paths
- XP bar + mini roadmap progress bars

## Key Dependencies

- **recharts** 2.15.2 — RadarChart
- **lucide-react** 0.487.0 — icons (includes MessageSquare, Bot, User, Send, etc.)
- **react-router-dom** 7.13.0 — routing
- **@clerk/clerk-react** — auth
- **@posthog/react** — analytics

## Constants

`src/app/constants/routes.ts` — route builders for dashboard, roadmaps, courses, quizzes
