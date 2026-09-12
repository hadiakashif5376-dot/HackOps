from typing import Dict
from prompts import PROJECT_PROMPT
from utils import extract_json_object, get_groq_client


def analyze_project(project_idea: str) -> Dict:
    """Convert a hackathon idea into structured MVP requirements."""
    if not project_idea.strip():
        raise ValueError("Project idea cannot be empty.")

    client = get_groq_client()
    prompt = PROJECT_PROMPT.format(project_idea=project_idea)
    response = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "Return only valid JSON. No markdown fences."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
    )
    data = extract_json_object(response.choices[0].message.content)

    data["project_idea"] = project_idea
    data.setdefault("summary", project_idea.strip())
    data.setdefault("mvp_goal", "Build a focused, demonstrable MVP.")
    data.setdefault("required_roles", [])
    data.setdefault("required_skills", [])
    data.setdefault("critical_capabilities", [])
    return data
