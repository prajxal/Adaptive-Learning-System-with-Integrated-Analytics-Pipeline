# Frontend Codemap

## Entry Point

`src/main.tsx` — Renders `<App />` wrapped in `ClerkProvider`, `PostHogProvider`, `PostHogErrorBoundary`, plus `TokenSynchronizer` and `PostHogIdentifier`.

## App Shell

`src/app/App.tsx` — `BrowserRouter` with route definitions. Protected routes render inside `AppLayout` (sidebar + navbar). Unauthenticated users redirect to `/signin`.

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
| `/progress` | MyProgressPage | `src/app/pages/MyProgressPage.tsx` |

## Shared Components

| Component | File |
|-----------|------|
| AppNavbar | `src/app/components/AppNavbar.tsx` |
| AppSidebar | `src/app/components/AppSidebar.tsx` |
| RecommendationPanel | `src/app/components/RecommendationPanel.tsx` |
| RoadmapNode | `src/app/components/RoadmapNode.tsx` |
| RoadmapContainer | `src/app/components/RoadmapContainer.tsx` |
| LoadingSkeleton | `src/app/components/LoadingSkeleton.tsx` |
| LemonButton/Card/Input/Modal/ProgressBar | `src/app/components/Lemon*.tsx` |

## API Service Layer

### Core API (`src/services/api.ts`)
Exports `BACKEND_URL` and `getClerkToken()` — used by all other API modules.

### Granular API Modules (`src/services/`)

| Module | File | Backend Endpoints Hit |
|--------|------|-----------------------|
| courseApi | `src/services/courseApi.ts` | `/courses` |
| roadmapApi | `src/services/roadmapApi.ts` | `/roadmaps` |
| progressApi | `src/services/progressApi.ts` | `/progress/*` |
| userApi | `src/services/userApi.ts` | `/users/me/*` |
| githubApi | `src/services/githubApi.ts` | `/github/*` |
| resumeApi | `src/services/resumeApi.ts` | `/resume/*` |

### Page-Level API (`src/app/services/`)

| Module | File |
|--------|------|
| api.ts | `src/app/services/api.ts` — `getRecommendation()`, `getUser()`, `sendEvent()` |
| auth.ts | `src/app/services/auth.ts` — `signup()`, `login()` |
| quizApi.ts | `src/app/services/quizApi.ts` — `getSkillProfile()`, `getQuiz()`, `submitQuizAttempt()` |

## Custom Hooks

| Hook | File |
|------|------|
| useCourses | `src/hooks/useCourses.ts` |
| useRoadmaps | `src/hooks/useRoadmaps.ts` |
| useProgress | `src/hooks/useProgress.ts` |
| useUserSkills | `src/hooks/useUserSkills.ts` |

## Auth Utilities

| File | Purpose |
|------|---------|
| `src/auth/TokenSynchronizer.tsx` | Clerk JWT synchronization |
| `src/auth/PostHogIdentifier.tsx` | PostHog user identification |
