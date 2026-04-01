"""
Gemini function declarations and tool dispatch table for the AI Mentor.
"""
from typing import Any, Callable

from mcp_server.tools import (
    get_next_course,
    get_roadmap_courses,
    get_skill_graph,
    get_user_profile,
    get_user_progress,
)

# ---------------------------------------------------------------------------
# Gemini function declarations (sent in every chat request)
# ---------------------------------------------------------------------------

TOOL_DECLARATIONS: list[dict] = [
    {
        "name": "get_user_profile",
        "description": (
            "Fetch the user's profile including their skills, Elo rating, XP, "
            "current level, and GitHub connection status."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "The internal user ID"}
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "get_user_progress",
        "description": (
            "Fetch the user's learning progress across all roadmaps they have engaged with. "
            "Returns completed courses count, total courses, and progress percentage per roadmap."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "The internal user ID"}
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "get_next_course",
        "description": (
            "Get the recommended next course for a user within a specific roadmap. "
            "Returns the top recommended course and up to 2 alternatives."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string", "description": "The internal user ID"},
                "roadmap_id": {
                    "type": "string",
                    "description": "The roadmap ID (e.g. 'frontend', 'backend', 'devops')",
                },
            },
            "required": ["user_id", "roadmap_id"],
        },
    },
    {
        "name": "get_roadmap_courses",
        "description": "List all courses in a roadmap with their difficulty level and required user level.",
        "parameters": {
            "type": "object",
            "properties": {
                "roadmap_id": {"type": "string", "description": "The roadmap ID"}
            },
            "required": ["roadmap_id"],
        },
    },
    {
        "name": "get_skill_graph",
        "description": (
            "Get the skill dependency graph for a roadmap showing prerequisites. "
            "If user_id is provided, also returns completion status (completed/unlocked/locked) per skill."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "roadmap_id": {"type": "string", "description": "The roadmap ID"},
                "user_id": {
                    "type": "string",
                    "description": "Optional: include to get per-skill completion status for this user",
                },
            },
            "required": ["roadmap_id"],
        },
    },
]

# ---------------------------------------------------------------------------
# Security: tools that accept a user_id — the router always overrides this
# with the authenticated user's ID so the LLM cannot query other users.
# ---------------------------------------------------------------------------

USER_ID_TOOLS: frozenset[str] = frozenset(
    {"get_user_profile", "get_user_progress", "get_next_course", "get_skill_graph"}
)

# ---------------------------------------------------------------------------
# Dispatch table: tool name → callable
# ---------------------------------------------------------------------------

TOOL_REGISTRY: dict[str, Callable[..., Any]] = {
    "get_user_profile": get_user_profile,
    "get_user_progress": get_user_progress,
    "get_next_course": get_next_course,
    "get_roadmap_courses": get_roadmap_courses,
    "get_skill_graph": get_skill_graph,
}
