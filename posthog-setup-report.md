<wizard-report>
# PostHog post-wizard report

The wizard has completed a deep integration of PostHog analytics into the AI Learning Path Generator. PostHog was initialized in `src/main.tsx` with `PostHogProvider` and `PostHogErrorBoundary` wrapping the entire app for automatic error capture. User identification is performed on both login and signup so all events are correlated to a known user. Fourteen custom events were instrumented across seven files covering the full user journey: authentication, onboarding (GitHub connect, resume upload), learning (resource viewing and completion), and assessment (quiz start, submission, retake). Exception tracking via `captureException` was added at key failure points. Environment variables (`VITE_PUBLIC_POSTHOG_KEY`, `VITE_PUBLIC_POSTHOG_HOST`) are used throughout — no keys are hardcoded.

## Files changed

| File | Changes |
|------|---------|
| `src/main.tsx` | Added `posthog.init`, `PostHogProvider`, `PostHogErrorBoundary` |
| `src/app/pages/Login.tsx` | `posthog.identify` on success; capture `user_logged_in`, `login_failed`, `captureException` |
| `src/app/pages/Signup.tsx` | `posthog.identify` on success; capture `user_signed_up`, `captureException` |
| `src/app/pages/DashboardPage.tsx` | Capture `github_connect_clicked`, `resume_uploaded`, `resume_processing_failed`, `continue_learning_clicked`, `captureException` |
| `src/app/pages/CourseDetailPage.tsx` | Capture `quiz_started` (with `retake` property) on both Take Quiz and Retake Quiz buttons |
| `src/app/pages/QuizPage.tsx` | Capture `quiz_submitted` (with score/passed/total_questions), `quiz_retaken`, `captureException` |
| `src/app/pages/ResourceViewerPage.tsx` | Capture `resource_opened` (on active resource change), `resource_completed` (on Mark Complete click) |
| `src/app/components/RecommendationPanel.tsx` | Capture `recommendation_course_clicked`, `recommended_roadmap_explored` |

## Events instrumented

| Event | Description | File |
|-------|-------------|------|
| `user_signed_up` | User successfully creates a new account | `src/app/pages/Signup.tsx` |
| `user_logged_in` | User successfully logs in | `src/app/pages/Login.tsx` |
| `login_failed` | Login attempt failed (invalid credentials or server error) | `src/app/pages/Login.tsx` |
| `github_connect_clicked` | User clicks Connect GitHub on the dashboard | `src/app/pages/DashboardPage.tsx` |
| `resume_uploaded` | User selects and uploads a resume PDF | `src/app/pages/DashboardPage.tsx` |
| `resume_processing_failed` | Resume processing completed with a failure status | `src/app/pages/DashboardPage.tsx` |
| `continue_learning_clicked` | User clicks Resume in the Continue Learning banner | `src/app/pages/DashboardPage.tsx` |
| `quiz_started` | User clicks Take Quiz or Retake Quiz on a course | `src/app/pages/CourseDetailPage.tsx` |
| `quiz_submitted` | User submits quiz answers and receives a score | `src/app/pages/QuizPage.tsx` |
| `quiz_retaken` | User clicks Retake Quiz after viewing results | `src/app/pages/QuizPage.tsx` |
| `resource_opened` | User navigates to a specific learning resource | `src/app/pages/ResourceViewerPage.tsx` |
| `resource_completed` | User marks a learning resource as complete | `src/app/pages/ResourceViewerPage.tsx` |
| `recommendation_course_clicked` | User clicks Start on a recommended course | `src/app/components/RecommendationPanel.tsx` |
| `recommended_roadmap_explored` | User clicks a suggested new roadmap in the recommendation panel | `src/app/components/RecommendationPanel.tsx` |

## Next steps

We've built some insights and a dashboard for you to keep an eye on user behavior, based on the events we just instrumented:

- **Dashboard — Analytics basics**: https://us.posthog.com/project/331544/dashboard/1331051
- **User Acquisition: Signups & Logins**: https://us.posthog.com/project/331544/insights/gJuaSlne
- **Quiz Completion Funnel**: https://us.posthog.com/project/331544/insights/wwBjdR4k
- **Learning Engagement: Resources Opened vs Completed**: https://us.posthog.com/project/331544/insights/3j6bws7W
- **Onboarding Funnel: Signup → GitHub → Resume**: https://us.posthog.com/project/331544/insights/vUjptGP2
- **Failure & Churn Signals**: https://us.posthog.com/project/331544/insights/En0LnmkM

### Agent skill

We've left an agent skill folder in your project at `.claude/skills/posthog-integration-react-react-router-7-declarative/`. You can use this context for further agent development when using Claude Code. This will help ensure the model provides the most up-to-date approaches for integrating PostHog.

</wizard-report>
