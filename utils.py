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
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON returned by the AI model: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("The AI response must be a JSON object.")

    return data


def groq_json_completion(
    client: Groq,
    model: str,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.1,
) -> Dict:
    """
    Ask Groq for JSON using JSON Object Mode.

    This is more reliable than asking for plain text JSON because Groq
    validates the response as JSON before returning it.
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        response_format={"type": "json_object"},
        reasoning_format="hidden",
    )

    content = response.choices[0].message.content or ""
    return extract_json_object(content)


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
