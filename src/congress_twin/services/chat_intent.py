"""
Chat intent + entity extraction for Hybrid semantic layer (Phase 1).

Uses LLM when chat_llm_api_key is set; otherwise regex fallback.
Intents: attention, critical_path, workload, impact, task_list, dependencies, milestone, monte_carlo, summary.
"""

import json
import logging
import re
from typing import Any

from congress_twin.config import get_settings

logger = logging.getLogger(__name__)

INTENTS = [
    "attention",
    "critical_path",
    "workload",
    "impact",
    "task_list",
    "dependencies",
    "milestone",
    "monte_carlo",
    "summary",
]


GROQ_BASE_URL = "https://api.groq.com/openai/v1"


def _extract_intent_llm(message: str, plan_id: str) -> dict[str, Any] | None:
    """Call LLM to get intent + entities. Uses Groq if GROQ_API_KEY set, else CHAT_LLM_API_KEY. Returns None on failure or if no key."""
    settings = get_settings()
    api_key = settings.groq_api_key or settings.chat_llm_api_key
    if not api_key:
        logger.info("chat_intent: LLM skipped — no GROQ_API_KEY or CHAT_LLM_API_KEY set")
        return None
    use_groq = bool(settings.groq_api_key)
    model = settings.groq_model if use_groq else settings.chat_llm_model
    base_url = GROQ_BASE_URL if use_groq else (settings.chat_llm_base_url or "default")
    logger.info("chat_intent: Calling LLM (provider=%s, model=%s) for message=%r", "groq" if use_groq else "chat_llm", model, message[:80])
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url=base_url,
        )
        prompt = f"""You are a planner assistant. Given the user message and current plan_id, return a single JSON object with:
- "intent": one of {json.dumps(INTENTS)}
- "entities": object with optional keys: plan_id (string), task_id (string, e.g. task-001), slippage_days (integer), event_date (ISO date string), status (notStarted|inProgress|completed), bucket_name (string)

Current plan_id: {plan_id}
User message: {message}

Reply with only the JSON object, no markdown or explanation."""
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        text = (resp.choices[0].message.content or "").strip()
        # Strip markdown code block if present
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        out = json.loads(text)
        intent = out.get("intent", "summary")
        if intent not in INTENTS:
            intent = "summary"
        entities = out.get("entities") or {}
        entities.setdefault("plan_id", plan_id)
        logger.info("chat_intent: LLM returned intent=%s", intent)
        return {"intent": intent, "entities": entities}
    except Exception as e:
        logger.warning("chat_intent: LLM call failed — %s: %s", type(e).__name__, e)
        return None


def _extract_intent_regex(message: str, plan_id: str) -> dict[str, Any]:
    """Regex-based intent + entity extraction (fallback when LLM disabled or fails)."""
    msg_lower = message.lower().strip()
    entities: dict[str, Any] = {"plan_id": plan_id}

    if re.search(r"attention|what needs|today|blocked|overdue|blockers", msg_lower):
        return {"intent": "attention", "entities": entities}
    if re.search(r"critical path|longest|chain", msg_lower):
        return {"intent": "critical_path", "entities": entities}
    if re.search(r"overload|workload|who is busy|assignee|who has", msg_lower):
        return {"intent": "workload", "entities": entities}
    if re.search(r"monte carlo|probability|on time|finish on time", msg_lower):
        return {"intent": "monte_carlo", "entities": entities}
    if re.search(r"milestone|at risk|event date|go-live|before.*date", msg_lower):
        return {"intent": "milestone", "entities": entities}
    if re.search(r"depend|upstream|downstream|what depends|what blocks", msg_lower):
        # Try to extract task_id (e.g. task-005)
        m = re.search(r"(task[-_]?\w+)", msg_lower)
        if m:
            entities["task_id"] = m.group(1).replace("_", "-")
        return {"intent": "dependencies", "entities": entities}
    if re.search(r"impact|delay|slip|affect", msg_lower):
        m = re.search(r"(task[-_]?\w+)", msg_lower)
        if m:
            entities["task_id"] = m.group(1).replace("_", "-")
        if re.search(r"\d+\s*day", msg_lower):
            m = re.search(r"(\d+)\s*day", msg_lower)
            if m:
                entities["slippage_days"] = int(m.group(1))
        if "slippage_days" not in entities:
            entities["slippage_days"] = 3
        return {"intent": "impact", "entities": entities}
    if re.search(r"task list|tasks in|in progress|completed|not started|bucket", msg_lower):
        if re.search(r"in progress|inprogress", msg_lower):
            entities["status"] = "inProgress"
        elif re.search(r"completed|done", msg_lower):
            entities["status"] = "completed"
        elif re.search(r"not started", msg_lower):
            entities["status"] = "notStarted"
        return {"intent": "task_list", "entities": entities}

    return {"intent": "summary", "entities": entities}


def extract_intent(message: str, plan_id: str) -> dict[str, Any]:
    """
    Extract intent and entities from user message.
    Tries LLM first if configured; falls back to regex.
    Returns: { "intent": str, "entities": { plan_id, task_id?, slippage_days?, event_date?, status?, bucket_name? } }
    """
    result = _extract_intent_llm(message, plan_id)
    if result is not None:
        return result
    fallback = _extract_intent_regex(message, plan_id)
    logger.info("chat_intent: Using regex fallback — intent=%s", fallback["intent"])
    return fallback
