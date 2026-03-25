# Product Overview

The AI Learning Path Generator is an adaptive learning system designed to create highly personalized, developer-focused learning curriculums. The system solves the problem of "tutorial hell" and unstructured learning by analyzing a user's existing skills and directly mapping them to industry-standard learning paths.

The core concept revolves around ingesting a user's background (via Resume and GitHub), automatically scoring their current proficiency on a standard curriculum graph (derived from roadmap.sh), and systematically guiding them to the best "next step" using a topological recommendation engine and an adaptive Elo rating system.

---

# System Architecture

The core architecture follows a standard full-stack web application structure with specific AI and data modules.

**Architecture Flow:**
User → React Frontend → FastAPI Backend → PostgreSQL Database → Recommendation Engine

- **Frontend:** React with Vite and TypeScript. It utilizes React Router for navigation and structured dashboard components.
- **Backend framework:** FastAPI (Python) serving REST API endpoints.
- **Database:** PostgreSQL accessed asynchronously / synchronously via SQLAlchemy ORM.
- **Analytics tools used:** PostHog is implemented on the frontend to track user behavior, page views, and interactions.
- **External integrations:** 
  - **Clerk:** Handles user authentication.
  - **GitHub API:** Fetches public repository and commit data.
  - **roadmap.sh JSONs:** Raw data source for structured curriculums.

---

# Database Schema

### `users`
- **Purpose:** Central entity for all users in the system.
- **Important fields:** `id`, `clerk_user_id`, `email`, `global_elo_rating` (defaults to 1000.0), `resume_status`, `github_status`.
- **Interactions:** One-to-many relationship with `user_skills` and `events`.

### `user_skills`
- **Purpose:** Stores the proficiency detail for particular skills as parsed or updated by quizzes.
- **Important fields:** `skill_name`, `proficiency_level`, `elo_rating`, `trust_score`.
- **Interactions:** Belongs to a single user.

### `events`
- **Purpose:** Replaces complex activity tracking with an event-driven JSON log. Logs application analytic events system-side.
- **Important fields:** `event_type`, `course_id`, `payload` (JSON).
- **Interactions:** Tied to `users`.

### `courses`
- **Purpose:** Represents individual learning topics/nodes extracted from a broader roadmap graph.
- **Important fields:** `id` (composite of roadmap_id:node_id), `roadmap_id`, `node_id`, `title`, `difficulty_level`.
- **Interactions:** Referenced by `course_prerequisites` (as both prerequisites and dependents) and `course_resources`.

### `course_prerequisites`
- **Purpose:** Defines the topological dependency graph (what course must be completed before another).
- **Important fields:** `course_id` (dependent), `prerequisite_id` (requirement).
- **Interactions:** Self-referential join table mapping `courses` to `courses`.

### `course_resources`
- **Purpose:** Stores the actual content (videos, articles) tied to course topics.
- **Important fields:** `course_id`, `resource_type`, `url`, `youtube_video_id`, `difficulty_level`.
- **Interactions:** Bound to `courses`.

*(Note: There are other models identified like `SkillWeight`, `SkillProfile`, and `QuizAttempt`, which store intermediate scoring and quiz histories).*

---

# Roadmap Graph

The backend utilizes `roadmap.sh` JSON files to formalize the curriculum structure.

- **Node extraction:** The system scans JSON files for nodes with a `type: "topic"`. It extracts the `label`/`title` and maps it to a `Course` model.
- **Prerequisite edges:** It parses the JSON edge arrays. The system uses a Breadth-First Search (BFS) to traverse from a source topic node through any non-topic sub-nodes until it hits another viable topic node. Direct dependencies are inserted into `course_prerequisites`.
- **How courses are represented:** Courses are identified globally using a `{roadmap_id}:{node_id}` format.
- **How difficulty is assigned:** Difficulty is computed via a script (`compute_difficulty.py`). The script measures the topological depth (distance from the root of the graph). The assigned difficulty formula is: `800 + (depth * 100)`.

---

# Skill Ingestion System

The ingestion system gathers unstructured user data and translates it into structured skill profiles.

### Resume ingestion:
- **Parsing method:** The system uses `pdfplumber` to extract raw text, normalizing it to lowercase.
- **Extracted skills:** It performs a regex frequency match for roadmap course IDs against the resume's text. The occurrences are normalized against the max_score to define a preliminary "weight" and bounded to a max "confidence" of 1.0 (calculated as `occurrences / 5.0`).

### GitHub ingestion:
- **Repositories analyzed:** Fetches all public, non-forked, unarchived repositories belonging to the user.
- **Languages detected:** Fetches the language byte-counts per repository using GitHub API.
- **Commits / activity metrics used:** Pulls commit counts categorized by the repository's primary language.
- **Skill conversion:** The script maps detected languages (e.g., Python, TypeScript) to internal roadmap skill strings (e.g., "python-developer", "typescript"). It calculates a `combined_weight` utilizing `(byte_weight * 0.6) + (commit_weight * 0.4)` and a confidence metric.

Finally, a `skill_synthesizer.py` or equivalent merges these disparate signal `SkillWeight` rows into a unified user `SkillProfile`.

---

# Confidence Score Logic

Confidence represents how reliable the system believes its current proficiency assessment is. 

- **Inputs used:** GitHub signals (`github_confidence`), Resume signals (`resume_confidence`), and Quiz signals (`quiz_confidence`).
- **Scoring formula:** Before quizzes, it assigns maximum confidence from either GitHub or the Resume. Once a quiz is taken, the quiz signal governs the final confidence. The quiz updates confidence progressively: `new_quiz_confidence = min(1.0, old_quiz_confidence + 0.2)`. A weighted EMA (Exponential Moving Average) determines overall proficiency combining history, new quiz execution, and old confidence ratings.
- **Meaning of low vs high confidence:** Low confidence implies the data is mostly inferred (from a brief resume mention). High confidence indicates robust evaluation (completed quizzes). High confidence anchors the user's proficiency level securely, requiring more effort to shift dramatically.

---

# Elo Rating System

The system implements a global Elo rating to match user capability against content difficulty.

- **What Elo represents:** It represents the user's software engineering capability relative to the objective difficulty of course topics. Minimum is 800, max is 2000.
- **Initial rating:** Assigned securely at *1000.0* via the `User` table defaults.
- **Formulas used:** Uses the standard logistic Elo expected score formula: `1 / (1 + 10 ^ ((course_elo - user_elo) / 400))`. Actual score mapping assigns 1.0 for quiz scores $\ge$ 80, 0.5 for $\ge$ 50, and 0.0 for $<$ 50. K-Factor is 32. 
- **Rating updates occur:** After the user completes a quiz (`update_skill_profile_from_quiz`).
- **How Elo interacts with course difficulty:** The user's Elo dynamically updates when evaluated on a course metric (where the course metric acts as the "opponent"). 

---

# Recommendation Algorithm

The system actively suggests the next most valuable topic to learn (`learning_priority_service.py`).

1. **Prerequisite filtering:** The function `get_unlocked_courses()` scans the database to find courses where all prerequisites are marked as fulfilled ("unlocked") and the course itself is not mathematically marked "completed".
2. **Difficulty matching:** *Not strictly implemented in the prioritized ranking logic.* The backend relies firmly on topology rather than adjusting for the user's Elo in the suggestion order.
3. **Ranking logic:** Calculates a topological importance score. `importance_score = (descendants_count * 3) + (out_degree * 2) + (10 - graph_depth)`. This prioritizes bottleneck subjects that unlock the most downstream skills.
4. **Final recommendation output:** Sorts all unlocked courses descending by importance. The system outputs the highest-scoring course as the `recommended` start, and the next top two as `alternatives`.

---

# User Interaction Flow

1. **User signup**: Creates Clerk auth.
2. **Skill ingestion**: User connects GitHub and uploads a Resume.
3. **Confidence scoring**: Synthesizer establishes cold-start skill levels & starting confidences.
4. **Initial Elo**: User automatically begins at ~1000 global Elo.
5. **Course recommendation**: Algorithm suggests the highest priority topological node they should learn.
6. **User actions**: User engages with resources.
7. **Elo updates**: User takes an assessment/quiz based on the course, updating their proficiency level and shifting their global Elo up or down.

---

# Analytics System

- **Analytics tools used:** PostHog initialized within the frontend stack (`src/auth/PostHogIdentifier.tsx`).
- **Events tracked:** Tracks user interaction points scattered across key pages (e.g., `DashboardPage`, `MyProgressPage`, `QuizPage`).
- **Metrics collected:** Identifies unique users and follows interaction funnels.
- **Usage for product:** Ensures UI/UX iterations evaluate where users drop off inside curriculums or struggle with quiz completion.

---

# Current Limitations

- **GitHub ingestion improvements:** Parsing relies purely on repository bytes and commits grouped by language. It utilizes a hardcoded `SKILL_LANGUAGE_MAP` which does not track frameworks (like React, Django) intricately inside package configurations.
- **Quiz system logic:** TBD robustness inside the adaptive generation for quizzes (how the prompt aligns with course contents deeply vs generatively).
- **Recommendation Logic:** The recommendation algorithm currently depends exclusively on structural graph topology and does not incorporate the Elo-adaptive difficulty metrics to find the "sweet spot" for users.

---

# Key Technical Innovations

- **Skill Inference from Unstructured Data**: Successfully translating vague bullet points in PDFs and Github API byte counts into structured `SkillWeights`.
- **Graph-based Curriculum Modeling**: Extracting raw diagram graph structures from `roadmap.sh` JSON files and algorithmically collapsing visual diagram nodes into strict relational backend prerequisite schemas via Breadth-First-Search. 
- **Elo-based Adaptive Learning for Tech**: Transplanting traditional chess Elo calculations securely onto software engineering competency, mapping courses as fixed-elo entities and users as volatile dynamic players.
