"""A small helper for asking Claude to review code.

If there is no API key (or the `anthropic` package isn't installed),
`claude_available()` returns False and Perenic uses rule-based checks only.
"""

import json
import os

MODEL = "claude-opus-5"

# The shape of the JSON we ask Claude to send back.
REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rule": {"type": "string"},
                    "message": {"type": "string"},
                    "severity": {"type": "string", "enum": ["info", "warning", "error"]},
                    "line": {"type": "integer"},
                },
                "required": ["rule", "message", "severity", "line"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "findings"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = (
    "You are a PAT (Perennial Artificial Testing) agent from PerenicAI: a code "
    "reviewer acting as a quality gate before code reaches production. Review "
    "the code you are given for bugs, security "
    "problems, error handling, readability and maintainability. Report every "
    "real issue you find with the line number it's on (use 0 if it isn't tied "
    "to a line). Use 'error' only for problems likely to break production. "
    "Keep each message to one or two sentences and say how to fix it."
)


def claude_available() -> bool:
    """True if we have what we need to call Claude."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def review_with_claude(code: str, filename: str, industry_guidance: str = "") -> dict:
    """Send code to Claude and return {"summary": ..., "findings": [...]}.

    `industry_guidance` is appended to the system prompt, e.g. HIPAA focus areas.

    Raises an exception if the request fails; the caller decides what to do.
    """
    import anthropic

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from the environment

    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        # If Claude declines a request, retry it on another suitable model.
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        system=f"{SYSTEM_PROMPT}\n\n{industry_guidance}".strip(),
        output_config={"format": {"type": "json_schema", "schema": REVIEW_SCHEMA}},
        messages=[
            {
                "role": "user",
                "content": f"Please review this file: {filename}\n\n```python\n{code}\n```",
            }
        ],
    )

    if response.stop_reason == "refusal":
        raise RuntimeError("Claude declined to review this code")

    text = next(block.text for block in response.content if block.type == "text")
    return json.loads(text)
