from typing import Dict, List
import re


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


_ALIASES = {
    "ai": ["ai", "machine learning", "llm", "artificial intelligence"],
    "backend": ["backend", "api", "fastapi", "flask", "node"],
    "frontend": ["frontend", "react", "javascript", "typescript", "ui"],
    "ui ux": ["ui", "ux", "figma", "design"],
    "database": ["database", "postgresql", "mysql", "sql", "mongodb"],
    "deployment": ["deployment", "docker", "cloud", "devops", "streamlit"],
    "product": ["product", "research", "presentation", "technical writer"],
    "data": ["data", "pandas", "data science"],
}

_EXPERIENCE_WEIGHT = {"beginner": 0.85, "intermediate": 1.0, "advanced": 1.1}


def _member_text(member: Dict) -> str:
    return " ".join(
        [_norm(member.get("primary_role", ""))]
        + [_norm(s) for s in member.get("skills", [])]
    )


def _match_count(capability: str, team: List[Dict]) -> int:
    """How many distinct team members have a skill/role touching this capability."""
    terms = _ALIASES.get(_norm(capability), [_norm(capability)])
    count = 0
    for member in team:
        text = _member_text(member)
        if any(term in text for term in terms):
            count += 1
    return count


def _capability_score(match_count: int) -> int:
    """
    Partial credit instead of a flat covered/not-covered binary:
    - 0 matches: weak, not covered
    - 1 match: covered, but a single point of failure
    - 2+ matches: solid, redundant coverage
    """
    if match_count <= 0:
        return 20
    if match_count == 1:
        return 60
    return min(100, 60 + (match_count - 1) * 20)


def evaluate_team(team: List[Dict], project: Dict) -> Dict:
    """Calculate realistic project capability coverage and team balance."""
    capabilities = project.get("critical_capabilities") or project.get("required_skills", [])
    coverage = []
    for capability in capabilities:
        matches = _match_count(capability, team)
        score = _capability_score(matches)
        coverage.append(
            {
                "capability": capability,
                "covered": matches > 0,
                "match_count": matches,
                "coverage_score": score,
            }
        )

    coverage_score = (
        sum(item["coverage_score"] for item in coverage) / len(coverage)
        if coverage else 60
    )

    # Role diversity: how many of the project's *required* roles are actually
    # represented on the team, not just "are the 4 team members different from
    # each other" (which is trivially true almost every time).
    required_roles = project.get("required_roles") or []
    required_norm = [_norm(r) for r in required_roles]
    if required_norm:
        represented = 0
        for req in required_norm:
            hit = any(
                req in _norm(m.get("assigned_role", m.get("primary_role", "")))
                or _norm(m.get("assigned_role", m.get("primary_role", ""))) in req
                for m in team
            )
            if hit:
                represented += 1
        diversity_score = represented / len(required_norm) * 100
    else:
        role_names = [_norm(m.get("assigned_role", m.get("primary_role", ""))) for m in team]
        diversity_score = min(100, len(set(role_names)) / max(1, len(team)) * 100)

    # Semantic match quality from the AI search step (leader has none — only
    # matched members carry a semantic_score), pulling the score toward how
    # genuinely well-matched the picks were, not just keyword presence.
    semantic_scores = [
        m.get("semantic_score") for m in team
        if isinstance(m.get("semantic_score"), (int, float))
    ]
    semantic_quality = (sum(semantic_scores) / len(semantic_scores)) if semantic_scores else 65

    # Experience mix nudges the score up or down slightly — an all-beginner
    # team and an all-advanced team shouldn't score identically.
    experience_values = [
        _EXPERIENCE_WEIGHT.get(_norm(m.get("experience_level", "intermediate")), 1.0)
        for m in team
    ]
    experience_factor = sum(experience_values) / len(experience_values) if experience_values else 1.0

    overall = (coverage_score * 0.5 + diversity_score * 0.25 + semantic_quality * 0.25) * experience_factor
    overall = round(min(100, max(0, overall)), 1)

    gaps = [item["capability"] for item in coverage if item["coverage_score"] < 60]
    strengths = [item["capability"] for item in coverage if item["coverage_score"] >= 60]

    return {
        "overall_score": overall,
        "coverage_score": round(coverage_score, 1),
        "role_diversity_score": round(diversity_score, 1),
        "coverage": coverage,
        "strengths": strengths[:8],
        "gaps": gaps[:8],
        "team_size": len(team),
    }
