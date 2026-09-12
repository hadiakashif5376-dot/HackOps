import json
import os
import re
from typing import Dict, List, Callable, Any

from dotenv import load_dotenv
from groq import Groq


def load_env() -> None:
    """Load environment variables from .env if present."""
    load_dotenv()


def get_groq_client() -> Groq:
    """Create a Groq client using GROQ_API_KEY."""
    load_env()
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is missing. Add it to .env or Streamlit secrets."
        )
    return Groq(api_key=key)


def extract_json_object(text: str) -> Dict:
    """Parse a JSON object returned by the model."""
    if not text:
        raise ValueError("The AI model returned an empty response.")

    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("The AI response did not contain a valid JSON object.")

    candidate = cleaned[start : end + 1]

    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        data = _parse_with_repairs(candidate)

    if not isinstance(data, dict):
        raise ValueError("The AI response must be a JSON object.")

    return data


def _parse_with_repairs(candidate: str) -> Dict:
    """
    Try a sequence of increasingly aggressive repairs on near-valid JSON.

    Order matters: fix the safest, most common issue first (raw control
    characters inside string values), then trailing commas / truncation,
    then both combined. Raises ValueError with the *last* parser error if
    nothing works.
    """
    attempts = []

    escaped = _escape_raw_control_chars_in_strings(candidate)
    attempts.append(escaped)

    attempts.append(_attempt_json_repair(candidate))
    attempts.append(_attempt_json_repair(escaped))

    last_exc = None
    for attempt in attempts:
        try:
            return json.loads(attempt)
        except json.JSONDecodeError as exc:
            last_exc = exc
            continue

    raise ValueError(f"Invalid JSON returned by the AI model: {last_exc}") from last_exc


def _escape_raw_control_chars_in_strings(text: str) -> str:
    """
    Escape literal newline / tab / carriage-return characters that appear
    inside JSON string literals.

    LLMs frequently emit multi-line text (e.g. a "summary" or "objective"
    field) with real line breaks instead of the escaped ``\\n`` JSON
    requires. That produces confusing "Expecting ',' delimiter" errors deep
    into the document, well before the response is actually truncated.
    """
    out = []
    in_string = False
    escape_next = False

    for ch in text:
        if in_string:
            if escape_next:
                out.append(ch)
                escape_next = False
                continue
            if ch == "\\":
                out.append(ch)
                escape_next = True
                continue
            if ch == '"':
                in_string = False
                out.append(ch)
                continue
            if ch == "\n":
                out.append("\\n")
                continue
            if ch == "\r":
                out.append("\\r")
                continue
            if ch == "\t":
                out.append("\\t")
                continue
            out.append(ch)
        else:
            if ch == '"':
                in_string = True
            out.append(ch)

    return "".join(out)


def _attempt_json_repair(candidate: str) -> str:
    """
    Best-effort cleanup for near-valid JSON coming back from an LLM.

    Handles the most common failure modes:
    - trailing commas before a closing bracket/brace
    - a response that got cut off mid-object/array (unbalanced brackets)
    """
    repaired = candidate

    # Remove trailing commas like `"a": 1,}` or `[1, 2,]`
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

    # If brackets/braces are unbalanced (likely truncated output), try closing them.
    open_curly = repaired.count("{")
    close_curly = repaired.count("}")
    open_square = repaired.count("[")
    close_square = repaired.count("]")

    if open_curly > close_curly or open_square > close_square:
        # Trim any dangling partial token/value after the last complete comma or brace,
        # then append the missing closers in a reasonable order.
        last_good = max(repaired.rfind(","), repaired.rfind("}"), repaired.rfind("]"))
        if last_good != -1 and last_good < len(repaired) - 1:
            repaired = repaired[: last_good + 1]
            repaired = re.sub(r",\s*$", "", repaired)

        repaired += "]" * (open_square - repaired.count("]"))
        repaired += "}" * (open_curly - repaired.count("}"))

    return repaired


def groq_json_completion(
    client: Groq,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
    max_tokens: int = 8192,
    _allow_repair_retry: bool = True,
) -> Dict:
    """
    Ask Groq for JSON using JSON Object Mode.

    This is more reliable than asking for plain text JSON because Groq
    validates the response as JSON before returning it. We also:
    - set an explicit max_tokens so large structured responses aren't
      silently truncated by a low default cap
    - detect truncated responses (finish_reason == "length") and raise
      a clear error instead of a confusing JSON parse failure
    - make one retry attempt asking the model to repair its own output
      if the JSON still fails to parse for a non-truncation reason
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        reasoning_format="hidden",
    )

    choice = response.choices[0]
    content = choice.message.content or ""

    if choice.finish_reason == "length":
        raise ValueError(
            "The AI response was cut off before it finished (hit the max_tokens "
            "limit). Try increasing max_tokens or shortening the input."
        )

    try:
        return extract_json_object(content)
    except ValueError:
        if not _allow_repair_retry:
            raise
        # One repair attempt: show the model its own broken output and ask
        # it to return a corrected, valid JSON object.
        repair_prompt = (
            "The text below was supposed to be a single valid JSON object, "
            "but it failed to parse. Return ONLY the corrected, valid JSON "
            "object and nothing else (no markdown, no commentary):\n\n"
            f"{content}"
        )
        return groq_json_completion(
            client=client,
            model=model,
            system_prompt=system_prompt,
            user_prompt=repair_prompt,
            temperature=0,
            max_tokens=max_tokens,
            _allow_repair_retry=False,
        )


def safe_json(data: Any) -> str:
    """Serialize application data for display/download."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def validate_participants(participants: List[Dict]) -> None:
    """
    Validate participant input requirements for a multi-project hackathon.

    Rules:
    - At least four participants overall (1 leader + 3 members minimum).
    - Every participant needs a name, and a bio or GitHub URL.
    - Names must be unique.
    - There can be MULTIPLE leaders — each running their own project — but
      every leader must supply a project idea.
    - There must be at least 3 members overall (a shared pool that leaders'
      teams are matched from).
    """
    if len(participants) < 4:
        raise ValueError("At least four participants are required (1 Leader + 3 Members).")

    names = set()
    leader_count = 0
    member_count = 0

    for participant in participants:
        name = str(participant.get("name", "")).strip()
        bio = str(participant.get("bio", "")).strip()
        github = str(participant.get("github", "")).strip()
        role = str(participant.get("role", "member")).strip().lower()

        if not name:
            raise ValueError("Every participant needs a name.")

        if not bio and not github:
            raise ValueError(f"{name} needs a bio or GitHub URL.")

        if name.lower() in names:
            raise ValueError(f"Duplicate participant name: {name}.")
        names.add(name.lower())

        if role == "leader":
            leader_count += 1
            if not str(participant.get("project_idea", "")).strip():
                raise ValueError(f"{name} is marked as a Leader but has no project idea.")
        else:
            member_count += 1

    if leader_count < 1:
        raise ValueError("At least one participant must be a Leader with a project idea.")

    if member_count < 3:
        raise ValueError("At least three Members are needed to form a team alongside a Leader.")
