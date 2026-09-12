from typing import Dict
from prompts import SPRINT_PROMPT
from utils import extract_json_object, get_groq_client


def generate_sprint_plan(team: list, project: Dict, balance: Dict) -> Dict:
    """Generate a structured, team-specific 48-hour hackathon execution plan."""
    client = get_groq_client()
    prompt = SPRINT_PROMPT.format(
        project=project,
        team=team,
        balance=balance,
    )
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "Return only valid JSON. No markdown fences."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    data = extract_json_object(response.choices[0].message.content)
    data.setdefault("overview", "A focused 48-hour MVP sprint.")
    data.setdefault("phases", [])
    data.setdefault("milestones", [])
    data.setdefault("demo_checklist", [])
    return data
