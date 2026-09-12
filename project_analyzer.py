from typing import Dict

from prompts import PROJECT_PROMPT
from utils import get_groq_client, groq_json_completion


MODEL = "openai/gpt-oss-120b"


def analyze_project(project_idea: str) -> Dict:
    """Convert a hackathon idea into structured MVP requirements."""
    if not project_idea.strip():
        raise ValueError("Project idea cannot be empty.")

    client = get_groq_client()
    prompt = PROJECT_PROMPT.format(project_idea=project_idea)

    data = groq_json_completion(
        client=client,
        model=MODEL,
        system_prompt=(
            "You are a hackathon product analyst. "
            "Return one valid JSON object matching the requested structure. "
            "Do not use markdown."
        ),
        user_prompt=prompt,
        temperature=0.1,
    )

    data["project_idea"] = project_idea
    data.setdefault("summary", project_idea.strip())
    data.setdefault("mvp_goal", "Build a focused, demonstrable MVP.")
    data.setdefault("required_roles", [])
    data.setdefault("required_skills", [])
    data.setdefault("critical_capabilities", [])
    data.setdefault("priorities", [])

    return data
