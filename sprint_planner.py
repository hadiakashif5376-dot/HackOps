from typing import Dict

from prompts import SPRINT_PROMPT
from utils import get_groq_client, groq_json_completion


MODEL = "openai/gpt-oss-120b"


def generate_sprint_plan(team: list, project: Dict, balance: Dict) -> Dict:
    """Generate a structured, team-specific 48-hour hackathon execution plan."""
    client = get_groq_client()
    prompt = SPRINT_PROMPT.format(
        project=project,
        team=team,
        balance=balance,
    )

    # This is the most verbose prompt in the app (full 48-hour coverage,
    # tasks for every team member, milestones, demo checklist), so it's
    # the most likely response to hit a token limit — give it extra room.
    data = groq_json_completion(
        client=client,
        model=MODEL,
        system_prompt=(
            "You are a hackathon execution planner. "
            "Return one valid JSON object matching the requested structure. "
            "Do not use markdown."
        ),
        user_prompt=prompt,
        temperature=0.2,
        max_tokens=10000,
    )

    data.setdefault("overview", "A focused 48-hour MVP sprint.")
    data.setdefault("phases", [])
    data.setdefault("milestones", [])
    data.setdefault("demo_checklist", [])

    return data
