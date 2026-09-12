from typing import Dict, List
import re


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _covered(capability: str, team: List[Dict]) -> bool:
    cap = _norm(capability)
    combined = " ".join(
        [_norm(m.get("primary_role", "")) for m in team]
        + [_norm(s) for m in team for s in m.get("skills", [])]
    )
    aliases = {
        "ai": ["ai", "machine learning", "llm", "artificial intelligence"],
        "backend": ["backend", "api", "fastapi", "flask", "node"],
        "frontend": ["frontend", "react", "javascript", "typescript", "ui"],
        "ui ux": ["ui", "ux", "figma", "design"],
        "database": ["database", "postgresql", "mysql", "sql", "mongodb"],
        "deployment": ["deployment", "docker", "cloud", "devops", "streamlit"],
        "product": ["product", "research", "presentation", "technical writer"],
        "data": ["data", "pandas", "data science"],
    }
    terms = aliases.get(cap, [cap])
    return any(term in combined for term in terms)


def evaluate_team(team: List[Dict], project: Dict) -> Dict:
    """Calculate project capability coverage and summarize team balance."""
    capabilities = project.get("critical_capabilities") or project.get("required_skills", [])
    coverage = []
    for capability in capabilities:
        covered = _covered(capability, team)
        coverage.append(
            {
                "capability": capability,
                "covered": covered,
                "coverage_score": 100 if covered else 25,
            }
        )

    covered_count = sum(1 for item in coverage if item["covered"])
    coverage_score = (covered_count / len(coverage) * 100) if coverage else 75

    role_names = [_norm(m.get("assigned_role", m.get("primary_role", ""))) for m in team]
    unique_roles = len(set(role_names))
    diversity_score = min(100, unique_roles / max(1, len(team)) * 100)

    overall = round(coverage_score * 0.75 + diversity_score * 0.25, 1)

    gaps = [item["capability"] for item in coverage if not item["covered"]]
    strengths = [item["capability"] for item in coverage if item["covered"]]

    return {
        "overall_score": overall,
        "coverage_score": round(coverage_score, 1),
        "role_diversity_score": round(diversity_score, 1),
        "coverage": coverage,
        "strengths": strengths[:8],
        "gaps": gaps[:8],
        "team_size": len(team),
    }
