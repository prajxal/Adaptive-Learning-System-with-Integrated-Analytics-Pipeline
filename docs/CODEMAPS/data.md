# Data Codemap

## Database

PostgreSQL (Supabase), accessed via SQLAlchemy ORM. Engine configured in `backend/db/database.py`.

## Models

### User — `backend/models/user.py`
Table: `users`. Central entity.
Columns: `id` (PK), `clerk_user_id`, `email`, `password_hash`, `skill_level`, `engagement_score`, `global_elo_rating` (default 1000.0), `resume_status`, `github_*` fields, `google_*` fields, `avatar_url`, `created_at`.
Relationships: `user_skills` → UserSkill, `events` → Event.

### UserSkill — `backend/models/user_skill.py`
Table: `user_skills`. Per-roadmap skill rating.
Columns: `id` (PK), `user_id` (FK→users), `skill_name`, `proficiency_level`, `elo_rating`, `trust_score`, `last_updated`.
Unique: (`user_id`, `skill_name`).

### Course — `backend/models/course.py`
Table: `courses`. Represents a topic node from roadmap.sh.
Columns: `id` (PK, format: `{roadmap_id}:{node_id}`), `roadmap_id`, `node_id`, `title`, `description`, `difficulty_level` (default 1000.0), `created_at`.

### CoursePrerequisite — `backend/models/course_prerequisite.py`
Table: `course_prerequisites`. Directed dependency edge.
Columns: `course_id` (FK→courses, the dependent), `prerequisite_id` (FK→courses, must be done first).
PK: (`course_id`, `prerequisite_id`).

### CourseResource — `backend/models/course_resource.py`
Table: `course_resources`. Learning materials linked to courses.
Columns: `id` (PK), `course_id` (FK→courses), `resource_type`, `title`, `url`, `platform`, `duration_seconds`, `difficulty_level`, `quality_score`, `is_primary`, `youtube_video_id`, `thumbnail_url`, `channel_name`, `view_count`, `created_at`, `generated_at`.

### Event — `backend/models/event.py`
Table: `events`. Analytics event log.
Columns: `id` (PK), `user_id` (FK→users), `event_type`, `course_id`, `roadmap_id`, `payload` (JSON), `created_at`.

### SkillWeight — `backend/models/skill_weight.py`
Table: `skill_weights`. Raw ingestion weights from github/resume/quiz.
PK: (`user_id`, `skill_name`, `source`). Columns: `weight`, `confidence`, `last_updated`.

### SkillProfile — `backend/models/skill_profile.py`
Table: `skill_profiles`. Synthesized proficiency per user per skill.
Columns: `id` (PK), `user_id` (FK→users), `skill_id`, `roadmap_id`, `proficiency_level`, `confidence`, `quiz_*`, `github_*`, `resume_*` proficiency/confidence pairs.
Unique: (`user_id`, `skill_id`).

### SkillEdge — `backend/models/skill_edge.py`
Table: `skill_edges`. Graph edges for skill sequencing.
Columns: `id` (PK), `roadmap_id`, `from_skill_id` (FK→courses), `to_skill_id` (FK→courses), `created_at`.
Unique: (`from_skill_id`, `to_skill_id`).

### SkillQuiz — `backend/models/skill_quiz.py`
Table: `skill_quizzes`. AI-generated quiz per course.
Columns: `id` (PK), `skill_id` (FK→courses), `questions` (JSON), `passing_score` (default 80), `created_at`.
Unique: `skill_id`.

### QuizAttempt — `backend/models/quiz_attempt.py`
Table: `quiz_attempts`. User quiz submission history.
Columns: `id` (PK), `user_id` (FK→users), `skill_id` (FK→courses), `score`, `passed`, `answers` (JSON), `created_at`.

## Entity Relationships

```
User
 ├── UserSkill (1:N via user_id)
 ├── Event (1:N via user_id)
 ├── SkillWeight (1:N via user_id)
 ├── SkillProfile (1:N via user_id)
 └── QuizAttempt (1:N via user_id)

Course
 ├── CoursePrerequisite (M:N self-referential)
 ├── CourseResource (1:N via course_id)
 ├── SkillEdge (M:N self-referential)
 ├── SkillQuiz (1:1 via skill_id)
 └── QuizAttempt (1:N via skill_id)
```

## Migrations

Location: `backend/migrations/` (Alembic config: `backend/alembic.ini`).

| Migration | File |
|-----------|------|
| Baseline schema | `versions/789321a178d7_baseline_schema.py` |
| Fix skill_weight PK | `versions/a1b2c3d4e5f6_fix_skill_weight_pk.py` |
| Drop skill_profile FK | `versions/b2c3d4e5f6a7_drop_skill_profile_fk.py` |
| Add clerk_user_id | `versions/75c7fce60b46_add_clerk_user_id_to_users.py` |
