def compute_required_level(topological_depth: int) -> int:
    """Convert topological depth (0-based) to required level (1-6).

    Depth 0 maps to level 1 (entry-level courses), depth 5+ maps to level 6
    (advanced courses). The result is clamped to [1, 6].
    """
    return min(6, max(1, topological_depth + 1))
