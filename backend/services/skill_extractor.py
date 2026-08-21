"""
Skill Extractor — "text → [{skill, confidence, source}]"

Pipeline:
  Resume text
  → tokenize / normalize lines
  → detect section headers (Skills, Technical Skills, …)
  → match aliases against SORTED_ALIASES (longest-first to avoid sub-string collisions)
  → apply section-boost: mentions inside a detected Skills section score 1.5×
  → build confidence from boosted counts

Optional semantic fallback (Phase 3):
  Set env var  RESUME_SEMANTIC_MATCH=1  to enable SBERT-based cosine matching.
  Requires:  pip install sentence-transformers
  The model is lazy-loaded on first call and cached at module level.
  Semantic matches are tagged with a 0.6× confidence multiplier (weaker than exact hits).

Output format (compatible with skill_synthesizer.py / SkillWeight):
  [{"skill": "javascript", "confidence": 0.45, "source": "resume"}]

IMPORTANT: This module does NOT write to the database and does NOT call
skill_synthesizer. That responsibility stays in resume_parser.ingest_resume.
"""

from __future__ import annotations

import os
import re
from typing import NamedTuple

from services.skill_alias_map import SORTED_ALIASES

# ---------------------------------------------------------------------------
# Section header vocabulary (ported from CVPipeline.FEATURE_HEADERS)
# ---------------------------------------------------------------------------
_SKILLS_HEADERS: set[str] = {
    "skills",
    "technical skills",
    "core skills",
    "skill highlights",
    "highlights",
    "technologies",
    "tools",
    "tech stack",
    "programming languages",
    "languages and frameworks",
}

_NON_SKILL_HEADERS: set[str] = {
    "summary",
    "professional summary",
    "career summary",
    "profile",
    "experience",
    "work experience",
    "professional experience",
    "employment history",
    "education",
    "education and training",
    "academic background",
    "certifications",
    "projects",
    "references",
    "awards",
    "publications",
    "interests",
    "hobbies",
}

# ---------------------------------------------------------------------------
# Helpers (ported / adapted from CVPipeline)
# ---------------------------------------------------------------------------

# Bullet characters commonly found in resume PDFs
_BULLET_RE = re.compile(r"[\u2022\u25cf\u25cb\u25aa\uf0b7\xb7\*\•]")


def clean_line(line: str) -> str:
    """Normalize a single resume line.

    - Strips unicode bullet characters and replaces them with commas so that
      "• React  • Docker" becomes "react , docker" after lowercasing.
    - Lowercases and removes non-ASCII noise.
    - Collapses whitespace and trims comma artefacts.
    """
    if not isinstance(line, str):
        return ""
    line = _BULLET_RE.sub(" , ", line)
    line = line.encode("ascii", errors="ignore").decode()
    line = line.lower().replace("&", " and ")
    line = re.sub(r"\s+", " ", line)
    line = re.sub(r"( , \s*)+", ", ", line)
    return line.strip().strip(",")


def is_header_line(line: str) -> bool:
    """Heuristic: a header is short, has no trailing period, and is ≤ 5 words."""
    if not line or len(line) > 50:
        return False
    if line.endswith(".") or len(line.split()) > 5:
        return False
    return True


def _classify_header(line: str) -> str | None:
    """Return 'skills', 'other', or None if the line is not a section header."""
    if not is_header_line(line):
        return None
    if line in _SKILLS_HEADERS:
        return "skills"
    if line in _NON_SKILL_HEADERS:
        return "other"
    # Prefix match (e.g. "skills:" or "technical skills:")
    for h in _SKILLS_HEADERS:
        if line.startswith(h + ":") or line.startswith(h + " "):
            return "skills"
    for h in _NON_SKILL_HEADERS:
        if line.startswith(h + ":"):
            return "other"
    return None


# ---------------------------------------------------------------------------
# Core extraction
# ---------------------------------------------------------------------------

class _SkillHit(NamedTuple):
    skill_id: str
    count: int          # raw occurrence count
    section_hits: int   # occurrences inside a Skills section


def _match_aliases_in_line(line: str) -> list[str]:
    """Return list of skill IDs matched in *line*, longest alias first.

    Tracks consumed character spans to avoid double-counting overlapping
    aliases (e.g. "react" inside "react native").
    """
    consumed: list[tuple[int, int]] = []
    matched: list[str] = []

    for alias, skill_id in SORTED_ALIASES:
        pattern = r"\b" + re.escape(alias) + r"\b"
        for m in re.finditer(pattern, line):
            start, end = m.start(), m.end()
            # Skip if this span overlaps any already-consumed span
            if any(s < end and start < e for s, e in consumed):
                continue
            consumed.append((start, end))
            matched.append(skill_id)

    return matched


def extract_skills_from_text(text: str) -> list[dict]:
    """Parse *text* and return a list of skill dicts.

    Each dict:
        {"skill": <canonical_skill_id>, "confidence": <float 0-1>, "source": "resume"}

    Algorithm:
      1. Split into lines; clean each line.
      2. Detect section header transitions.
      3. For lines in a Skills section, accumulate section_hits (1.5× weight bonus).
      4. For all lines, accumulate raw counts.
      5. Compute confidence = min(1.0, (count + 2 * section_hits) / 6.0).
    """
    counts: dict[str, int] = {}
    section_hits: dict[str, int] = {}

    in_skills_section = False

    for raw_line in text.split("\n"):
        line = clean_line(raw_line)
        if not line:
            continue

        header_type = _classify_header(line)
        if header_type == "skills":
            in_skills_section = True
            continue
        if header_type == "other":
            in_skills_section = False
            continue

        hits = _match_aliases_in_line(line)
        for skill_id in hits:
            counts[skill_id] = counts.get(skill_id, 0) + 1
            if in_skills_section:
                section_hits[skill_id] = section_hits.get(skill_id, 0) + 1

    if not counts:
        return []

    results: list[dict] = []
    for skill_id, count in counts.items():
        s_hits = section_hits.get(skill_id, 0)
        confidence = min(1.0, (count + 2 * s_hits) / 6.0)
        results.append({
            "skill": skill_id,
            "confidence": round(confidence, 4),
            "source": "resume",
        })

    return results


# ---------------------------------------------------------------------------
# Optional Phase 3: SBERT semantic fallback
# ---------------------------------------------------------------------------

_sbert_model = None  # lazy-loaded singleton


def _load_sbert():
    global _sbert_model
    if _sbert_model is None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            _sbert_model = SentenceTransformer("all-MiniLM-L6-v2")
            print("[SkillExtractor] SBERT model loaded (semantic matching enabled).")
        except ImportError:
            print(
                "[SkillExtractor] WARNING: sentence-transformers not installed. "
                "Semantic matching disabled. Run: pip install sentence-transformers"
            )
    return _sbert_model


def _semantic_skill_match(
    candidate_phrases: list[str],
    threshold: float = 0.72,
) -> list[dict]:
    """Use SBERT cosine similarity to match candidate phrases against canonical skill IDs.

    Only called when RESUME_SEMANTIC_MATCH=1.  Matches are given a 0.6×
    confidence multiplier to reflect that they are weaker than exact alias hits.

    Returns the same list[dict] format as extract_skills_from_text so results
    can be merged.
    """
    model = _load_sbert()
    if model is None:
        return []

    import torch  # type: ignore  # noqa: PLC0415

    canonical_ids = list({v for _, v in SORTED_ALIASES})
    canonical_embs = model.encode(canonical_ids, convert_to_tensor=True)
    phrase_embs = model.encode(candidate_phrases, convert_to_tensor=True)

    cos_scores = torch.nn.functional.cosine_similarity(
        phrase_embs.unsqueeze(1), canonical_embs.unsqueeze(0), dim=2
    )  # shape: [n_phrases, n_skills]

    results: list[dict] = []
    for i, phrase in enumerate(candidate_phrases):
        best_score, best_idx = cos_scores[i].max(dim=0)
        if best_score.item() >= threshold:
            skill_id = canonical_ids[best_idx.item()]
            results.append({
                "skill": skill_id,
                "confidence": round(0.6 * best_score.item(), 4),
                "source": "resume",
            })

    return results


def extract_skills_with_semantic_fallback(text: str) -> list[dict]:
    """Run the full extraction pipeline including optional SBERT fallback.

    Primary results come from extract_skills_from_text (alias matching).
    If RESUME_SEMANTIC_MATCH=1, unmatched candidate phrases from the Skills
    section are additionally scored via SBERT and merged in.

    The merged output de-duplicates on skill_id, keeping the higher-confidence
    result for any collision.
    """
    primary = extract_skills_from_text(text)
    primary_ids = {r["skill"] for r in primary}

    if os.getenv("RESUME_SEMANTIC_MATCH") != "1":
        return primary

    # Collect candidate phrases from Skills sections only
    candidate_phrases: list[str] = []
    in_skills = False
    for raw_line in text.split("\n"):
        line = clean_line(raw_line)
        if not line:
            continue
        htype = _classify_header(line)
        if htype == "skills":
            in_skills = True
            continue
        if htype == "other":
            in_skills = False
            continue
        if in_skills:
            # Split CSV-style lists inside skills sections
            for phrase in re.split(r"[,|/]", line):
                phrase = phrase.strip()
                if phrase and phrase not in primary_ids:
                    candidate_phrases.append(phrase)

    if not candidate_phrases:
        return primary

    semantic = _semantic_skill_match(candidate_phrases)
    # Merge: primary wins on collision
    for entry in semantic:
        if entry["skill"] not in primary_ids:
            primary.append(entry)
            primary_ids.add(entry["skill"])

    return primary
