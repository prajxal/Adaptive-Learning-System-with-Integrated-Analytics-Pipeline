"""
AI Mentor chat endpoint.

Runs a Gemini function-calling loop: the model can call MCP tools to fetch
real user data before composing its reply. Max 5 tool-call rounds per request.

Reliability: tries the primary model first. On 503 or timeout, falls back to
GEMINI_FALLBACK_MODEL for up to 2 retries before returning a graceful message.
"""
import logging
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.clerk_auth import get_current_user
from mcp_server.registry import TOOL_DECLARATIONS, TOOL_REGISTRY, USER_ID_TOOLS
from mcp_server.tools import build_user_context
from models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

_PRIMARY_MODEL  = os.getenv("GEMINI_CHAT_MODEL", "gemini-3-flash-preview")
_FALLBACK_MODEL = os.getenv("GEMINI_FALLBACK_MODEL", "gemini-2.5-flash")

# attempt 1: primary  |  attempts 2–3: fallback
GEMINI_MODEL_CHAIN: list[str] = [_PRIMARY_MODEL, _FALLBACK_MODEL, _FALLBACK_MODEL]

SYSTEM_PROMPT = (
    "You are an AI learning mentor for LearnPath AI, an adaptive learning platform. "
    "You help users understand their learning progress, answer questions about courses and roadmaps, "
    "and guide them on what to learn next. "
    "Always use the available tools to fetch real user data before answering — "
    "never make up statistics, course names, or progress numbers. "
    "Be encouraging, concise, and specific. "
    "When a user asks about their progress, skills, or next steps, call the relevant tools first."
)

MAX_TOOL_ROUNDS = 5

# Sentinel raised inside the tool-calling loop to signal a retryable Gemini error.
# Caught by the outer model-chain loop; never surfaces to the caller.
class _GeminiUnavailable(Exception):
    pass


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_user),
) -> ChatResponse:
    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="AI Mentor is not available (GEMINI_API_KEY not configured)",
        )

    user_id = str(current_user.id)

    # Pre-load user context once and inject into every attempt's system prompt.
    # This lets the model answer common questions ("What should I study?") without
    # needing tool-call round-trips to discover the active roadmap.
    try:
        user_context = build_user_context(user_id)
    except Exception as exc:
        logger.warning("build_user_context failed for user %s: %s", user_id, exc)
        user_context = ""

    dynamic_prompt = (
        SYSTEM_PROMPT + "\n\n" + user_context if user_context else SYSTEM_PROMPT
    )

    async with httpx.AsyncClient(timeout=60.0) as client:
        for attempt, model in enumerate(GEMINI_MODEL_CHAIN):
            url = f"{GEMINI_BASE_URL}/{model}:generateContent?key={GEMINI_API_KEY}"

            # Rebuild conversation state fresh for each attempt
            contents: list[dict] = [{"role": "user", "parts": [{"text": body.message}]}]
            payload: dict = {
                "system_instruction": {"parts": [{"text": dynamic_prompt}]},
                "tools": [{"function_declarations": TOOL_DECLARATIONS}],
                "contents": contents,
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
            }

            try:
                for _ in range(MAX_TOOL_ROUNDS):
                    resp = await client.post(
                        url, json=payload, headers={"Content-Type": "application/json"}
                    )

                    if resp.status_code == 503:
                        next_model = GEMINI_MODEL_CHAIN[attempt + 1] if attempt + 1 < len(GEMINI_MODEL_CHAIN) else None
                        logger.warning(
                            "chat: %s attempt %d returned 503 — %s",
                            model,
                            attempt + 1,
                            f"retrying with {next_model}" if next_model else "no more retries",
                        )
                        raise _GeminiUnavailable()

                    if resp.status_code != 200:
                        logger.error("Gemini chat %d: %s", resp.status_code, resp.text[:300])
                        raise HTTPException(status_code=502, detail="AI service error")

                    data = resp.json()
                    candidate = data.get("candidates", [{}])[0]
                    content = candidate.get("content", {})
                    parts = content.get("parts", [])

                    function_calls = [p["functionCall"] for p in parts if "functionCall" in p]

                    if not function_calls:
                        # No tool calls — the model has produced its final reply
                        text_parts = [p.get("text", "") for p in parts if "text" in p]
                        reply = " ".join(text_parts).strip()
                        if not reply:
                            reply = (
                                "I'm sorry, I wasn't able to answer that. "
                                "Try asking about your progress or what to learn next."
                            )
                        return ChatResponse(reply=reply)

                    # Append the model's tool-call turn to the conversation
                    contents.append({"role": "model", "parts": parts})

                    # Execute each tool call and collect results
                    tool_response_parts = []
                    for fc in function_calls:
                        tool_name: str = fc["name"]
                        args: dict = dict(fc.get("args", {}))

                        # Security: always use the authenticated user's ID —
                        # prevents the LLM from being tricked into querying another user.
                        if tool_name in USER_ID_TOOLS:
                            args["user_id"] = user_id

                        tool_fn = TOOL_REGISTRY.get(tool_name)
                        if tool_fn is None:
                            result: dict = {"error": f"Unknown tool: {tool_name}"}
                        else:
                            try:
                                result = tool_fn(**args)
                            except Exception as exc:
                                logger.warning("Tool %s raised: %s", tool_name, exc)
                                result = {"error": str(exc)}

                        tool_response_parts.append(
                            {"functionResponse": {"name": tool_name, "response": result}}
                        )

                    contents.append({"role": "user", "parts": tool_response_parts})
                    payload["contents"] = contents

            except _GeminiUnavailable:
                # 503 from this model — outer loop will try the next one
                continue

            except httpx.TimeoutException:
                next_model = GEMINI_MODEL_CHAIN[attempt + 1] if attempt + 1 < len(GEMINI_MODEL_CHAIN) else None
                logger.warning(
                    "chat: %s attempt %d timed out — %s",
                    model,
                    attempt + 1,
                    f"retrying with {next_model}" if next_model else "no more retries",
                )
                continue

            except httpx.RequestError as exc:
                # Network-level failure (DNS, connection refused) — no point retrying
                logger.error("Gemini network error on attempt %d: %s", attempt + 1, exc)
                return ChatResponse(
                    reply="I'm having trouble reaching the AI service. Please try again in a moment."
                )

    logger.error("chat: all %d model attempts failed for user %s", len(GEMINI_MODEL_CHAIN), user_id)
    return ChatResponse(
        reply="The AI Mentor is temporarily unavailable. Please try again in a moment."
    )
