from typing import Dict

from prompts import PROFILE_PROMPT
from utils import extract_json_object, get_groq_client, groq_json_completion


MODEL = "openai/gpt-oss-120b"


def parse_participant(participant: Dict) -> Dict:
    """Parse one participant bio into a structured profile."""
    name = participant.get("name", "Unknown Participant")
    bio = participant.get("bio", "")
    github = participant.get("github", "")

    if not bio.strip() and not github.strip():
        raise ValueError(f"{name} has neither a bio nor a GitHub URL.")

    client = get_groq_client()

    prompt = PROFILE_PROMPT.format(
        name=name,
        bio=bio or "Not provided",
        github=github or "Not provided",
    )

    data = groq_json_completion(
        client=client,
        model=MODEL,
        system_prompt=(
            "You are a profile extraction system. "
            "Return one valid JSON object matching the requested structure. "
            "Do not use markdown."
        ),
        user_prompt=prompt,
        temperature=0.1,
    )

    data["name"] = name
    data["bio"] = bio
    data["github"] = github
    data["skills"] = list(dict.fromkeys(data.get("skills", [])))
    data["primary_role"] = data.get("primary_role", "General Developer")
    data["experience_level"] = data.get("experience_level", "Intermediate")
    data["interests"] = data.get("interests", [])
    data["preferences"] = data.get("preferences", [])

    return data
