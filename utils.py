import ast
import json
import os
import re
from typing import Dict, List, Any

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


def _clean_model_text(text: str) -> str:
    """Remove common markdown wrappers around an AI response."""
    cleaned = (text or "").strip()

    # Remove markdown code fences.
    cleaned = re.sub(
        r"^```(?:json|JSON)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"\s*```$",
                     "",
                     cleaned)

    # If the model added text before/after the JSON, isolate the outer object.
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start != -1 and end > start:
        cleaned = cleaned[start : end + 1]

    return cleaned.strip()


def _repair_json(text: str) -> str:
    """
    Repair a few common LLM JSON mistakes.

    This is a safety net only. The first parser always tries normal JSON.
    """
    repaired = text.strip()

    # Remove trailing commas before } or ].
    repaired = re.sub(r",\s*([}\]])", r"\1", repaired)

    # Quote simple unquoted object keys:
    # { name: "Hadia" } -> { "name": "Hadia" }
    repaired = re.sub(
        r'([{,]\s*)([A-Za-z_][A-Za-z0-9_-]*)\s*:',
        r'\1"\2":',
        repaired,
    )

    return repaired


def extract_json_object(text: str) -> Dict:
    """
    Parse a JSON object returned by the model.

    Normal JSON is preferred. A small repair fallback handles common
    formatting mistakes so one bad model response does not crash HackOps.
    """
    if not text:
        raise ValueError("The AI model returned an empty response.")

    cleaned = _clean_model_text(text)

    # 1. Standard JSON.
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError as first_error:
        json_error = first_error

    # 2. Small syntax repairs.
    repaired = _repair_json(cleaned)

    try:
        data = json.loads(repaired)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    # 3. Python-literal fallback.
    # Handles cases such as {'name': 'Hadia'} or True/False/None.
    try:
        data = ast.literal_eval(repaired)
        if isinstance(data, dict):
            return data
    except (ValueError, SyntaxError):
        pass

    # Return a useful error pointing to the original JSON parser problem.
    raise ValueError(
        f"Invalid JSON returned by the AI model: {json_error}"
    )


def groq_json_completion(
    client: Groq,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.0,
) -> Dict:
    """
    Ask Groq for a JSON object with retry protection.

    JSON Object Mode asks Groq for valid JSON. If a malformed response
    nevertheless reaches the application, we retry the request with a
    stricter instruction before failing.
    """
    last_error = None

    for attempt in range(3):
        if attempt == 0:
            current_system = system_prompt
        else:
            current_system = (
                system_prompt
                + "\n\nCRITICAL OUTPUT RULE: "
                  "Return ONLY one valid JSON object. "
                  "Use double quotes around every property name and string. "
                  "Use commas between all properties. "
                  "Do not include markdown, comments, explanations, or trailing commas."
            )

        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": current_system,
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                temperature=0,
                response_format={"type": "json_object"},
                reasoning_format="hidden",
            )

            content = response.choices[0].message.content or ""
            return extract_json_object(content)

        except ValueError as exc:
            last_error = exc

            # Give the model one more explicit correction instruction.
            user_prompt = (
                user_prompt
                + "\n\nIMPORTANT: Your previous output could not be parsed. "
                  "Return ONLY valid JSON. Do not use single quotes. "
                  "Every object key must be enclosed in double quotes."
            )

        except Exception as exc:
            # API/network errors should be surfaced immediately.
            raise RuntimeError(f"Groq request failed: {exc}") from exc

    raise ValueError(str(last_error))


def safe_json(data: Any) -> str:
    """Serialize application data for display/download."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def validate_participants(participants: List[Dict]) -> None:
    """Validate participant input requirements."""
    if len(participants) < 4:
        raise ValueError("At least four participants are required.")

    names = set()

    for participant in participants:
        name = str(participant.get("name", "")).strip()
        bio = str(participant.get("bio", "")).strip()
        github = str(participant.get("github", "")).strip()

        if not name:
            raise ValueError("Every participant needs a name.")

        if not bio and not github:
            raise ValueError(f"{name} needs a bio or GitHub URL.")

        if name.lower() in names:
            raise ValueError(f"Duplicate participant name: {name}.")

        names.add(name.lower())
