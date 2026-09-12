from typing import Dict, List, Set
import re


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _skill_overlap(skills: List[str], required: List[str]) -> int:
    skill_text = " ".join(_norm(s) for s in skills)
    return sum(1 for r in required if _norm(r) in skill_text)


def _role_match(profile: Dict, required_roles: List[str]) -> int:
    text = _norm(profile.get("primary_role", ""))
    return sum(1 for role in required_roles if _norm(role) in text or text in _norm(role))


def _score(profile: Dict, project: Dict, selected: List[Dict]) -> float:
    required_skills = project.get("required_skills", [])
    role_score = _role_match(profile, project.get("required_roles", []))
    skill_score = _skill_overlap(profile.get("skills", []), required_skills)
    semantic = float(profile.get("semantic_score", 0))

    existing_skills: Set[str] = {
        _norm(skill)
        for member in selected
        for skill in member.get("skills", [])
    }
    unique_bonus = sum(1 for s in profile.get("skills", []) if _norm(s) not in existing_skills)

    return semantic * 0.45 + role_score * 12 + skill_score * 8 + unique_bonus * 2


def form_team(candidates: List[Dict], project: Dict, team_size: int = 4) -> List[Dict]:
    """Greedily form a complementary team using project-aware scoring."""
    if len(candidates) < team_size:
        raise ValueError("Not enough candidates to form a team.")

    remaining = list(candidates)
    selected: List[Dict] = []

    # First, favor candidates aligned with distinct required roles.
    while remaining and len(selected) < team_size:
        best = max(remaining, key=lambda p: _score(p, project, selected))
        remaining.remove(best)

        role = best.get("primary_role", "General Developer")
        required_roles = project.get("required_roles", [])
        if required_roles:
            role = min(
                required_roles,
                key=lambda r: abs(
                    _role_match(best, [r]) - 1
                )
            ) if _role_match(best, required_roles) else role

        member = dict(best)
        member["assigned_role"] = role
        member["selection_reason"] = (
            f"Semantic project match {best.get('semantic_score', 0):.0f}% "
            f"with complementary skills for the squad."
        )
        selected.append(member)

    return selected
