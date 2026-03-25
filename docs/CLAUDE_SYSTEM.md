# Claude Code System Overview

This customized Claude system turns a generic AI into a structured, highly reliable engineering assistant tailored specifically for the LearnPathAI repository. By providing a rigid scaffolding of workflows, it forces the AI to operate algorithmically rather than reactively. 

Without this structure, Claude is prone to "context loss," where past decisions are forgotten during extended sessions, and "hallucinations," where it might invent packages, reinvent database schemas, or accidentally rewrite functional logic. This system prevents those issues by embedding all essential facts, rules, and design patterns directly into Claude’s operating environment. Instead of jumping straight into coding and potentially making catastrophic mistakes, Claude is constrained by specific rules and pre-trained to use systematic commands and agents that mirror a disciplined human engineering team.

--------------------------------

# Claude System Architecture

The ecosystem relies on an interaction flowchart that guarantees structured execution:

**Developer** → Provides an instruction or invokes a Command 
**Commands** (`/plan`, `/build-fix`) → Funnel the developer's intent into an orchestrated workflow.
**Agents** (`planner.md`, `architect.md`) → Claude adopts a specialized persona (e.g., stopping all coding to act only as a planner).
**Skills** (`docker-patterns.md`, `python-testing.md`) → Deep-dive reference documents Claude loads on-demand to execute tasks without guessing API specifics.
**Rules** (`python-security.md`, `agents.md`) → Invisible, continuous constraints that force the code format and development workflow to adhere to project standards.
**Hooks** (`hooks.json`, `session-stop.sh`) → Passive listeners that execute external shell scripts autonomously to capture state.
**Memory** (`project-memory.json`, `project-map.json`) → Persistent core knowledge loaded into every new conversation to establish absolute context.

--------------------------------

# Claude Directory Structure

Here is the exact repository footprint of the configured Claude system:

```text
.claude
 ├ agents
 │  ├ architect.md
 │  ├ build-error-resolver.md
 │  ├ code-reviewer.md
 │  ├ doc-updater.md
 │  ├ planner.md
 │  └ refactor-cleaner.md
 │
 ├ commands
 │  ├ build-fix.md
 │  ├ context-budget.md
 │  ├ learn-eval.md
 │  ├ model-route.md
 │  ├ plan.md
 │  ├ python-review.md
 │  ├ refactor-clean.md
 │  ├ resume-session.md
 │  ├ save-session.md
 │  ├ update-codemaps.md
 │  └ verify.md
 │
 ├ rules
 │  ├ agents.md
 │  ├ development-workflow.md
 │  ├ git-workflow.md
 │  ├ performance.md
 │  ├ python-coding-style.md
 │  ├ python-hooks.md
 │  ├ python-patterns.md
 │  ├ python-security.md
 │  └ testing.md
 │
 ├ skills
 │  ├ agentic-engineering.md
 │  ├ ai-regression-testing.md
 │  ├ api-design.md
 │  ├ autonomous-loops.md
 │  ├ backend-patterns.md
 │  ├ benchmark.md
 │  ├ cloud-infrastructure-security.md
 │  ├ codebase-onboarding.md
 │  ├ coding-standards.md
 │  ├ continuous-agent-loop.md
 │  ├ database-migrations.md
 │  ├ deep-research.md
 │  ├ deployment-patterns.md
 │  ├ docker-patterns.md
 │  ├ documentation-lookup.md
 │  ├ frontend-patterns.md
 │  ├ integration-react-react-router-7-declarative
 │  ├ postgres-patterns.md
 │  ├ posthog-integration-react-react-router-7-declarative
 │  ├ python-patterns.md
 │  ├ python-testing.md
 │  ├ safety-guard.md
 │  ├ security-review.md
 │  ├ security-scan.md
 │  ├ strategic-compact.md
 │  ├ tdd-workflow.md
 │  └ verification-loop.md
 │
 ├ hooks
 │  ├ hooks.json
 │  └ session-stop.sh
 │
 └ memory
    ├ project-map.json
    └ project-memory.json

CLAUDE.md
```

--------------------------------

# Agents

Agents restrict Claude to single-minded operational personas, avoiding scattered thinking.

- **architect.md**  
  **Purpose:** Software architecture specialist for system design, evaluating scalability trade-offs, and documenting Architecture Decision Records (ADRs).  
  **When Used:** When designing net-new systems or undertaking major refactors.  
  **Interaction:** Invoked implicitly via design requests.

- **build-error-resolver.md**  
  **Purpose:** Surgical debugging expert. Reverts its behavior to strict analytical modes rather than creative generation.  
  **When Used:** When build failures or test errors halt development.  
  **Interaction:** Triggered directly via the `/build-fix` command.

- **code-reviewer.md**  
  **Purpose:** Objective quality assurance. Evaluates written code against conventions and security rules.  
  **When Used:** Prior to performing Git commits to catch edge cases, missing error handling, and performance anomalies.  
  **Interaction:** Often paired implicitly after feature completion or explicitly via review requests.

- **doc-updater.md**  
  **Purpose:** Documentation maintenance.  
  **When Used:** After architectural shifts or new feature builds. Keeps system overviews (like READMEs) in sync with reality.  
  **Interaction:** Used when a major implementation phase concludes.

- **planner.md**  
  **Purpose:** Development planning specialist. Ingests raw requirements, assesses dependencies, predicts risk factors, and writes phased execution steps.  
  **When Used:** Before a single line of code is produced for a feature.  
  **Interaction:** Triggered directly by the `/plan` command. The planner halts action until the user types a confirmation.

- **refactor-cleaner.md**  
  **Purpose:** Technical debt reduction. Uses strict, safe-deletion loops.  
  **When Used:** Triggered to identify and remove dead code, unused dependencies, or repetitive functions.  
  **Interaction:** Triggered directly by the `/refactor-clean` command. Follows atomic Git tracking rules.

--------------------------------

# Commands

Commands abstract lengthy prompt engineering into robust, reproducible macro-workflows.

| Command | Purpose | When to Use |
|-------|---------|-------------|
| `/plan` | Feature planning | At the start of any new feature or major change. Invokes the `planner` agent. |
| `/build-fix` | Build diagnostics | When a compiler, linter, or strict test suite fails. Invokes `build-error-resolver`. |
| `/context-budget` | Token optimization | When the AI context window is full. Forces contextual prioritization. |
| `/learn-eval` | Knowledge extraction | Identifies debugging patterns from a session and saves them permanently as reusable `.md` skills. |
| `/model-route` | LLM optimization | Directs task routing configurations for optimal cost/capability ratios. |
| `/python-review` | Code quality audit | Executes `code-reviewer` checks specific to FastAPI and Python nuances. |
| `/refactor-clean` | Debt removal | To surgically delete unused files, exports, or dependencies with verified test coverage. |
| `/resume-session` | Context restoration | At the start of a coding session, to reload specific feature knowledge from disk. |
| `/save-session` | State extraction | Before closing a session, logging what succeeded, what failed, and exact next steps. |
| `/update-codemaps` | Index synchronization | Executed to refresh internal abstract mappings when files shift significantly. |
| `/verify` | QA checklist | Forces execution of integration checks and rules tests prior to finalization. |

Each command functions as an autonomous script containing robust prompts, ensuring that Claude follows a predetermined checklist for every macro-operation instead of improvising.

--------------------------------

# Skills

Skills are modular, dense documentation files instructing Claude precisely on *how* to use technical patterns within the ecosystem. Claude only parses the necessary skills at runtime.

- **Framework Integrations:** Files like `integration-react-react-router-7-declarative` and `posthog-integration-react-react-router-7-declarative` grant deep fluency. Claude references these so it does not hallucinate outdated React Router v6 paradigms.
- **Backend Strategies:** `backend-patterns.md`, `python-patterns.md`, `postgres-patterns.md`, and `database-migrations.md` ensure Python is written defensively, using Alembic migrations properly and optimizing FastAPI performance.
- **Agentic Workflows:** Meta-skills like `autonomous-loops.md`, `tdd-workflow.md`, `ai-regression-testing.md`, and `deep-research.md` train Claude on its own operational pacing, reinforcing testing behaviors.
- **Security Guardrails:** `security-review.md`, `security-scan.md`, `cloud-infrastructure-security.md`, and `safety-guard.md` provide essential defensive knowledge against SQL injection, leaked secrets, and authentication bypass. 

--------------------------------

# Rules

Rules are pervasive guardrails. Whenever Claude interacts with specific file types, the intersecting rules strictly govern the AI's boundaries.

- **Syntax & Language Defaults:** `python-coding-style.md` and `python-patterns.md` force immutability defaults, explicit type annotations, and active compliance with black/ruff formats.
- **Operational Boundaries:** `agents.md` limits how agents interact in parallel and establishes orchestration rules. `testing.md` and `development-workflow.md` dictate how tests are constructed and how feature increments escalate.
- **Security Checkpoints:** `python-security.md` forces environment variable handling over hardcoding any secrets, pointing Claude strictly to FastAPI documentation for safe security contexts.
- **File System Automation:** `python-hooks.md` teaches Claude that formatting actions executed by `black` or `ruff` operate automatically, shifting responsibility off standard generation constraints. `git-workflow.md` enforces atomic commit sizing.

These operate invisibly; the moment Claude edits `main.py`, the Python-labeled rules engage.

--------------------------------

# Hooks

Hooks directly stitch the AI into the machine's terminal execution cycle without relying on human interaction.

- **Session Stop Ledger**  
  **Event Trigger:** `Stop` (As defined securely inside `.claude/hooks/hooks.json`). This event fires globally whenever Claude concludes an output response stream.  
  **Script Triggered:** `bash .claude/hooks/session-stop.sh`  
  **What it Modifies:** `.claude/memory/session-log.json`  
  **Problem it Solves:** Every time Claude completes a response, the bash script reads standard input (the JSON payload sent by Claude's client) to extract a `transcript_path`. It then timestamps an entry into the local ledger indicating whether the session was successfully updated. This acts as a perfect passive audit trail, confirming Claude's presence and linking human-readable progress checkpoints safely inside the local file system.

--------------------------------

# Memory System

Claude mitigates the severe limitation of "zero context at session start" entirely via memory files.

- **project-memory.json:** Hardcoded architectural facts. Upon booting, Claude learns the tech choices (React, FastAPI), platform limits (Elo defaults at 1000 with boundaries 800-2000), and specific deployment pipelines. It forces reality onto the AI context window.
- **project-map.json:** An internal routing table that drastically cuts search times. It maps exact conceptual names to files—e.g., `github_skill_extractor` equates instantly to `backend/services/github_skill_extractor.py`.
- **Session Files (`~/.claude/sessions/`):** Ephemeral operational states saved via `/save-session` and loaded via `/resume-session`. This bridges long-term consistency between yesterday's work and today's problems by forcing Claude to read identical debug logs.

--------------------------------

# Typical Development Workflow

By chaining the `.claude/` mechanics together, human developers follow this cadence:

1. **Start Claude:** Launch the interface inside the LearnPathAI root directory. `CLAUDE.md` and `.claude/memory/` files inherently load.
2. **Continue Progress:** Execute `/resume-session` to ingest yesterday's recorded trajectory.
3. **Plan Action:** Execute `/plan New Feature`. Wait for the `planner.md` agent to propose architecture changes, schema iterations, and potential risk mitigation.
4. **Approve:** Submit approval. Claude executes using skills like `frontend-patterns.md` or `database-migrations.md`.
5. **Quality Review:** Execute `/verify` to ensure the generated modules align securely against the requirements.
6. **Extract Patterns:** If a unique infrastructure hurdle was solved, run `/learn-eval` to extract that specific knowledge into persistent `skills/`.
7. **Document State:** Execute `/save-session` describing current broken, completed, or untried logic to safeguard for the next shift. 
8. **End Session:** The `Stop` hook invisibly timestamps the conclusion inside the session ledger.

--------------------------------

# Extending the Claude System

Adding custom behaviors translates directly into creating simple markdown files.

- **a new agent:** Create an explicitly scoped prompt in `.claude/agents/[name].md`. Define `name:`, `description:`, and operational boundaries inside standard markdown text to enforce a specific persona.
- **a new command:** Place a file in `.claude/commands/[action].md` declaring what triggers this macro workflow and detailing the multi-step checklist it must traverse when called.
- **a new rule:** Add a file inside `.claude/rules/`. Declare specific file path inclusion paths in the frontmatter `paths: - "**/*.extension"`, and list the coding restrictions underneath.
- **a new skill:** Detail architectural or API methodologies in `.claude/skills/`. Use `/learn-eval` to automate saving complex bug fixes as new skills seamlessly.
- **a new hook:** Map an event (like `Stop`, `Start`, `PreToolUse`, `PostToolUse`) inside `.claude/hooks/hooks.json` to a local executable shell script in the `.claude/hooks/` folder to inject real CLI tasks.

--------------------------------

# Key Takeaways

The custom `.claude` configuration structurally restricts AI improvisation without sacrificing speed. 

It upgrades the interaction from a simple chat interface to a fully-staffed digital engineering department. By assigning personas (Agents), providing macro checklists (Commands), and permanently documenting failure patterns (Skills/Memory), it elevates **reliability**. The strict mapping to repository guidelines natively blocks context drift, maximizing **architectural consistency**. Ultimately, by handing off entire operational lifecycles like technical planning, dependency refactoring, and code QA back to automated tooling, the overall **development velocity** fundamentally accelerates.
