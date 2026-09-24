import os
import json
import re

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

QUESTION_PROMPTS = {
    "at_risk": "Which clients are at risk and why?",
    "farm_gaps": "Which farm/segment gaps matter most today?",
    "local_market": "Why are apples going local, and what is their estimated value?",
}

SYSTEM_PROMPT = """You explain an already-computed apple export allocation plan to a
Production/Commercial planning committee. You do not calculate, allocate, or change
anything — the numbers are final and given to you as JSON.

Rules:
- Use ONLY the numbers and IDs in the provided JSON. Never invent a farm_id, client_id,
  or figure that is not present in it.
- Every farm_id or client_id you mention must literally appear in the JSON.
- If the question cannot be answered from the JSON, say plainly that it's unavailable.
- Answer in 2-4 short sentences, plain language, no markdown.
"""


def is_configured() -> bool:
    return bool(GROQ_API_KEY)


def _extract_valid_ids(context: dict) -> set:
    ids = set()
    for cid in (context.get("client_statuses") or {}).keys():
        ids.add(cid)
    for row in context.get("local_residual") or []:
        if row.get("farm_id"):
            ids.add(row["farm_id"])
    return ids


def ask_assistant(question_id: str, context: dict) -> dict:
    """Returns {'answer': str, 'evidence_ids': [str]}.
    Raises RuntimeError if no key configured (caller should return 501/424) or on failure.
    """
    if not is_configured():
        raise RuntimeError("NO_KEY")

    question_text = QUESTION_PROMPTS.get(question_id)
    if not question_text:
        raise ValueError(f"Unknown question_id: {question_id}")

    # Minimal structured context only — never raw farm/client sheets.
    payload_context = {
        "client_statuses": context.get("client_statuses"),
        "local_residual": context.get("local_residual"),
        "kpis": context.get("kpis"),
    }

    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)

        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": (
                    f"Question: {question_text}\n\n"
                    f"Computed plan data (JSON):\n{json.dumps(payload_context)}"
                )},
            ],
            temperature=0.2,
            max_tokens=300,
            timeout=8,
        )
        answer_text = resp.choices[0].message.content.strip()
    except Exception as e:
        raise RuntimeError(f"PROVIDER_FAILURE: {e}")

    # Validate: strip any ID the model mentions that isn't real, don't trust it blindly.
    valid_ids = _extract_valid_ids(context)
    mentioned = set(re.findall(r'\b([CF]\d{2,3})\b', answer_text))
    evidence_ids = sorted(mentioned & valid_ids)

    unknown_ids = mentioned - valid_ids
    if unknown_ids:
        # Model hallucinated an ID that doesn't exist in the plan — reject the answer
        # rather than show fabricated evidence.
        raise RuntimeError(f"UNGROUNDED_ID: {unknown_ids}")

    return {"answer": answer_text, "evidence_ids": evidence_ids}