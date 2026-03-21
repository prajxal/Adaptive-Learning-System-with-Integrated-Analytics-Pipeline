<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into your LearnPathAI project. PostHog was already strongly integrated (SDK installed, `PostHogProvider` + `PostHogErrorBoundary` configured in `src/main.tsx`, user identification via `src/auth/PostHogIdentifier.tsx`, and events tracked across 8 files). This session extended coverage by:

- **Setting environment variables**: `VITE_PUBLIC_POSTHOG_KEY` and `VITE_PUBLIC_POSTHOG_HOST` written to `.env`
- **Adding 2 new events**: `github_synced` (when GitHub sync succeeds) in `DashboardPage.tsx`, and `roadmap_progress_clicked` (when user clicks a roadmap from the Progress page) in `MyProgressPage.tsx`
- **Expanding error tracking**: Added `posthog.captureException()` in the GitHub polling error handler (`DashboardPage.tsx`) and the data fetch error handler (`MyProgressPage.tsx`)
- **Wiring up PostHog** in `MyProgressPage.tsx` which previously had no PostHog integration

## All instrumented events

| Event | Description | File |
|-------|-------------|------|
| `signup_cta_clicked` | User clicks "Get Started Free" or "Create Free Account" CTA. Properties: `location` | `src/app/pages/LandingPage.tsx` |
| `explore_roadmaps_clicked` | User clicks "Explore Roadmaps" CTA. Properties: `location` | `src/app/pages/LandingPage.tsx` |
| `roadmap_selected` | User clicks a roadmap card in the catalog. Properties: `roadmap_id`, `has_progress` | `src/app/pages/RoadmapCatalogPage.tsx` |
| `course_selected` | User clicks an unlocked course in a roadmap. Properties: `course_id`, `roadmap_id`, `course_title`, `difficulty_level` | `src/app/pages/RoadmapDetailPage.tsx` |
| `github_connect_clicked` | User clicks "Connect GitHub" on the dashboard | `src/app/pages/DashboardPage.tsx` |
| `resume_uploaded` | User uploads a resume PDF. Properties: `file_name`, `file_size` | `src/app/pages/DashboardPage.tsx` |
| `resume_processing_failed` | Resume processing failed after upload | `src/app/pages/DashboardPage.tsx` |
| `github_sync_failed` | GitHub sync polling failed | `src/app/pages/DashboardPage.tsx` |
| `github_synced` *(new)* | GitHub sync completed successfully. Properties: `repo_count`, `language_count` | `src/app/pages/DashboardPage.tsx` |
| `continue_learning_clicked` | User clicks "Resume" in the Continue Learning banner. Properties: `course_title`, `course_id` | `src/app/pages/DashboardPage.tsx` |
| `roadmap_progress_clicked` *(new)* | User clicks a roadmap card on the My Progress page. Properties: `roadmap_id`, `progress_percent` | `src/app/pages/MyProgressPage.tsx` |
| `quiz_started` | User clicks "Take Quiz" or "Retake Quiz". Properties: `course_id`, `course_title`, `retake` | `src/app/pages/CourseDetailPage.tsx` |
| `quiz_submitted` | User submits quiz answers. Properties: `course_id`, `score`, `passed`, `total_questions` | `src/app/pages/QuizPage.tsx` |
| `quiz_retaken` | User retakes a quiz from the results screen. Properties: `course_id`, `previous_score` | `src/app/pages/QuizPage.tsx` |
| `resource_opened` | User navigates to a learning resource. Properties: `course_id`, `resource_id`, `resource_title`, `resource_type`, `platform` | `src/app/pages/ResourceViewerPage.tsx` |
| `resource_completed` | User marks a resource as complete. Properties: `course_id`, `resource_id`, `resource_title`, `resource_type`, `platform` | `src/app/pages/ResourceViewerPage.tsx` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- **Dashboard — Analytics basics**: https://us.posthog.com/project/331544/dashboard/1383487
- **User Learning Funnel** (signup CTA → roadmap selected → course selected → quiz submitted): https://us.posthog.com/project/331544/insights/Fj7o5Izr
- **Daily Learning Engagement** (resources opened vs completed per day): https://us.posthog.com/project/331544/insights/81YLNNdu
- **Quiz Pass/Fail Rate by Week** (quiz outcomes broken down by pass/fail): https://us.posthog.com/project/331544/insights/T8xHquAu
- **GitHub & Resume Onboarding Actions** (GitHub connect, sync success, and resume upload rates): https://us.posthog.com/project/331544/insights/OqxMIOVW
- **Course Completion Funnel** (course selected → resource opened → resource completed → quiz started): https://us.posthog.com/project/331544/insights/CiZ3akyA

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/integration-react-react-router-7-declarative/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
