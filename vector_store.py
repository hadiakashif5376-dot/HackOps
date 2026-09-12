from typing import Dict, List, Tuple
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


_MODEL = None


def get_embedding_model():
    """Load the embedding model once and reuse it."""
    global _MODEL
    if _MODEL is None:
        _MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return _MODEL


def profile_to_text(profile: Dict) -> str:
    """Create stable text used for semantic embedding."""
    return (
        f"Role: {profile.get('primary_role', '')}. "
        f"Skills: {', '.join(profile.get('skills', []))}. "
        f"Experience: {profile.get('experience_level', '')}. "
        f"Interests: {', '.join(profile.get('interests', []))}. "
        f"Preferences: {', '.join(profile.get('preferences', []))}."
    )


def build_profile_index(profiles: List[Dict]) -> Tuple[faiss.IndexFlatIP, List[Dict]]:
    """Create a normalized FAISS inner-product index from profiles."""
    model = get_embedding_model()
    texts = [profile_to_text(p) for p in profiles]
    vectors = model.encode(texts, normalize_embeddings=True)
    vectors = np.asarray(vectors, dtype="float32")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)
    metadata = [{"index": i, "profile": p} for i, p in enumerate(profiles)]
    return index, metadata


def search_candidates(
    index: faiss.IndexFlatIP,
    metadata: List[Dict],
    project: Dict,
    top_k: int = 12,
) -> List[Dict]:
    """Retrieve semantically relevant participant profiles for a project."""
    model = get_embedding_model()
    project_text = (
        f"Project: {project.get('summary', '')}. "
        f"Roles: {', '.join(project.get('required_roles', []))}. "
        f"Skills: {', '.join(project.get('required_skills', []))}. "
        f"Capabilities: {', '.join(project.get('critical_capabilities', []))}."
    )
    vector = model.encode([project_text], normalize_embeddings=True)
    vector = np.asarray(vector, dtype="float32")

    scores, ids = index.search(vector, min(top_k, len(metadata)))
    candidates = []
    for score, idx in zip(scores[0], ids[0]):
        if idx >= 0:
            item = dict(metadata[idx]["profile"])
            item["semantic_score"] = round(float(score) * 100, 2)
            candidates.append(item)
    return candidates
