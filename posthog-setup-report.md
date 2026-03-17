<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into your LearnPathAI project. PostHog was already partially integrated (SDK installed, `PostHogProvider` + `PostHogErrorBoundary` configured in `src/main.tsx`, user identification via `src/auth/PostHogIdentifier.tsx`, and several events already tracked). This session extended coverage by:

- **Setting environment variables**: `VITE_PUBLIC_POSTHOG_KEY` and `VITE_PUBLIC_POSTHOG_HOST` written to `.env.local`.
- **Adding 3 new event capture locations** across the landing page, roadmap catalog, and roadmap detail pages to fill in gaps in top-of-funnel and learning journey tracking.
- **Preserving all existing events** already in place (quiz, resource, dashboard onboarding events, recommendations).

## Files changed this session

| File | Changes |
|------|---------|
| `src/app/pages/LandingPage.tsx` | Added `usePostHog`; capture `signup_cta_clicked` on hero and bottom CTAs, `explore_roadmaps_clicked` on Explore Roadmaps button |
| `src/app/pages/RoadmapCatalogPage.tsx` | Added `usePostHog`; capture `roadmap_selected` when user clicks a roadmap card |
| `src/app/pages/RoadmapDetailPage.tsx` | Added `usePostHog`; capture `course_selected` when user clicks an unlocked course card |

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
| `github_sync_failed` | GitHub sync failed after connecting | `src/app/pages/DashboardPage.tsx` |
| `continue_learning_clicked` | User clicks "Resume" in the Continue Learning banner. Properties: `course_title`, `course_id` | `src/app/pages/DashboardPage.tsx` |
| `quiz_started` | User clicks "Take Quiz" or "Retake Quiz". Properties: `course_id`, `course_title`, `retake` | `src/app/pages/CourseDetailPage.tsx` |
| `quiz_submitted` | User submits quiz answers. Properties: `course_id`, `score`, `passed`, `total_questions` | `src/app/pages/QuizPage.tsx` |
| `quiz_retaken` | User retakes a quiz from the results screen. Properties: `course_id`, `previous_score` | `src/app/pages/QuizPage.tsx` |
| `resource_opened` | User navigates to a learning resource. Properties: `course_id`, `resource_id`, `resource_title`, `resource_type`, `platform` | `src/app/pages/ResourceViewerPage.tsx` |
| `resource_completed` | User marks a resource as complete. Properties: `course_id`, `resource_id`, `resource_title`, `resource_type`, `platform` | `src/app/pages/ResourceViewerPage.tsx` |
| `recommendation_course_clicked` | User clicks a recommended course | `src/app/components/RecommendationPanel.tsx` |
| `recommended_roadmap_explored` | User clicks a suggested new roadmap | `src/app/components/RecommendationPanel.tsx` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- **Dashboard — Analytics basics**: https://us.posthog.com/project/331544/dashboard/1368968
- **Learning Path Conversion Funnel** (signup CTA → roadmap → course → quiz started → quiz submitted): https://us.posthog.com/project/331544/insights/iqjCgXUF
- **Daily Active Events Overview** (trend of key actions over 30 days): https://us.posthog.com/project/331544/insights/HvR8N2WI
- **Resume & GitHub Onboarding Events** (onboarding rates + failure tracking): https://us.posthog.com/project/331544/insights/iOTVDr7L
- **Resource Engagement** (resources opened vs completed): https://us.posthog.com/project/331544/insights/NJUjT2y6
- **Quiz Performance** (quiz starts, submissions, retakes per day): https://us.posthog.com/project/331544/insights/3H777zak

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/integration-react-react-router-7-declarative/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
