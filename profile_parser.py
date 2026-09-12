from typing import Dict
from groq import Groq
from prompts import PROFILE_PROMPT
from utils import extract_json_object, get_groq_client


def parse_participant(participant: Dict) -> Dict:
    """Parse one messy participant bio into a validated structured profile."""
    name = participant.get("name", "Unknown Participant")
    bio = participant.get("bio", "")
    github = participant.get("github", "")

    if not bio.strip() and not github.strip():
        raise ValueError(f"{name} has neither a bio nor a GitHub URL.")

    client = get_groq_client()
    prompt = PROFILE_PROMPT.format(name=name, bio=bio, github=github or "Not provided")
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "Return only valid JSON. No markdown fences."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    data = extract_json_object(response.choices[0].message.content)

    data["name"] = name
    data["bio"] = bio
    data["github"] = github
    data["skills"] = list(dict.fromkeys(data.get("skills", [])))
    data["primary_role"] = data.get("primary_role", "General Developer")
    data["experience_level"] = data.get("experience_level", "Intermediate")
    data["interests"] = data.get("interests", [])
    data["preferences"] = data.get("preferences", [])
    return data
