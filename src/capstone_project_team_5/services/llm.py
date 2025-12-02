from __future__ import annotations

# LLM helper using provider pattern
from collections.abc import Sequence

from capstone_project_team_5.services.llm_providers import LLMError
from capstone_project_team_5.services.llm_service import LLMService


def _normalize_bullets(text: str) -> list[str]:
    lines = [ln.strip() for ln in text.splitlines()]
    out: list[str] = []
    for ln in lines:
        if not ln:
            continue
        for prefix in ("- ", "• ", "* ", "•", "-"):
            if ln.startswith(prefix):
                ln = ln[len(prefix) :].strip()
                break
        out.append(ln)
    return out


def build_analysis_prompt(
    *,
    language: str,
    framework: str | None,
    skills: Sequence[str] | None = None,
    tools: Sequence[str] | None = None,
) -> str:
    parts: list[str] = [f"Language: {language}"]
    if framework:
        parts.append(f"Framework: {framework}")
    if skills:
        parts.append("Skills: " + ", ".join(sorted(set(skills))))
    if tools:
        parts.append("Tools: " + ", ".join(sorted(set(tools))))
    return " | ".join(parts)


def generate_bullet_points_from_analysis(
    *,
    language: str,
    framework: str | None,
    practices: Sequence[str] | None = None,
    tools: Sequence[str] | None = None,
    max_bullets: int = 5,
) -> list[str]:
    """Call LLM to produce resume-ready STAR bullets.

    The prompt aims for ATS-friendly, STAR-format bullets with strict formatting:
    - 4–6 bullets (capped by max_bullets)
    - One sentence per bullet, 14–25 words
    - Start with a strong action verb
    - Active voice, no first-person pronouns
    - Mention only provided technologies; do not invent metrics or tools
    - Output lines prefixed with "- " only
    """
    try:
        llm_service = LLMService()
    except Exception as e:
        raise LLMError(f"Failed to initialize LLM service: {e}") from e

    tools_set = set(tools or [])
    practices_set = set(practices or [])
    tools_str = ", ".join(sorted(tools_set)) or "None"
    practices_str = ", ".join(practices_set) or "None"

    system_rules = (
        "You are an expert resume writer generating concise, ATS-friendly, STAR-format bullets "
        "for a software project. Output exactly between 4 and "
        f"{max_bullets} bullets. One sentence per bullet (14–25 words). Start with a strong "
        "action verb. Use active voice. Do not use first-person pronouns. Use only the "
        "provided technologies; do not hallucinate tech or metrics. Prefer measurable outcomes "
        "when available; otherwise use truthful scope descriptors. Return bullets only: lines "
        "prefixed with '- ' and nothing else."
    )

    user_context = (
        "Context for resume bullets (generate STAR-format bullets):\n\n"
        "Primary stack:\n"
        f"- Language: {language}\n"
        f"- Framework: {framework or 'None'}\n"
        f"- Tools: {tools_str}\n"
        f"- Practices: {practices_str}\n\n"
        "Derivation guidelines (use only if supported by the stack/signals):\n"
        "- If REST/HTTP framework present: highlight API design, validation, and error handling.\n"
        "- If ORM/models present: note schema design, migrations, data integrity.\n"
        "- If tests present: emphasize reliability and regression prevention.\n"
        "- If CI/workflows present: automation and quality gates.\n"
        "- If containerization present: reproducible dev/deploy.\n"
        "- If linters/formatters present: code quality and consistency.\n\n"
        "Output: return only '- ' prefixed bullets, with the result or impact last."
    )

    # Generate response using LLM service
    try:
        text = llm_service.generate_llm_response(
            system_instructions=system_rules,
            user_content=user_context,
            temperature=0.7,
            max_tokens=None,
            seed=None,
        )
    except Exception as e:
        raise LLMError(f"LLM API call failed: {e}") from e

    return _normalize_bullets(text)
