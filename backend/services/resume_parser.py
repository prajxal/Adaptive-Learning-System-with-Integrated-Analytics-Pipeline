"""
Resume Parser — "PDF bytes → SkillWeight rows"

Pipeline:
  Resume PDF
  → text extraction   (PyMuPDF primary, pdfplumber fallback)
  → cleaning / normalisation   (handled inside skill_extractor)
  → skill detection            (alias matching + optional SBERT)
  → SkillWeight upsert
  → skill synthesis

The extraction quality was improved in Phase 1-2 of the resume-parser
upgrade (see skill_extractor.py and skill_alias_map.py):
  • PyMuPDF handles multi-column layouts better than pdfplumber
  • Section-header detection boosts confidence for explicitly listed skills
  • Aliases are matched longest-first to avoid sub-string collisions

Output contract (unchanged from original):
  SkillWeight(user_id, skill_name, weight, confidence, source="resume")

Weight hierarchy (unchanged):
  quiz > engagement > github > resume
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.skill_weight import SkillWeight
from services.github_skill_extractor import synthesize_all_skills_for_user
from services.skill_extractor import extract_skills_with_semantic_fallback


def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from a PDF file.

    Tries PyMuPDF (fitz) first — better at multi-column layouts, bullet lists,
    and dense resume formatting.  Falls back to pdfplumber on any error so that
    PDFs with unusual structure still get processed.

    Returns the full document text (NOT lowercased — normalisation happens
    inside skill_extractor.clean_line per line).
    """
    print(f"[ResumeParser] Starting text extraction from {file_path}")

    try:
        import fitz  # PyMuPDF  # noqa: PLC0415

        doc = fitz.open(file_path)
        text = "\n".join(page.get_text("text") for page in doc)
        print(
            f"[ResumeParser] PyMuPDF extraction successful. "
            f"Extracted {len(text)} characters."
        )
        return text
    except Exception as exc:
        print(f"[ResumeParser] PyMuPDF failed ({exc}); falling back to pdfplumber.")

    import pdfplumber  # noqa: PLC0415

    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += (page.extract_text() or "") + "\n"

    print(
        f"[ResumeParser] pdfplumber extraction successful. "
        f"Extracted {len(text)} characters."
    )
    return text


def ingest_resume(file_path: str, user_id: str, db: Session) -> None:
    """Full resume ingestion pipeline.

    1. Extract text from PDF.
    2. Detect skills (alias matching + optional SBERT semantic fallback).
    3. Upsert SkillWeight rows with source="resume".
    4. Trigger skill synthesis.

    This function's signature and SkillWeight output contract are unchanged
    from the original implementation.
    """
    print(f"[ResumeParser] Ingestion initiated for user {user_id}")

    text = extract_text_from_pdf(file_path)
    skill_results = extract_skills_with_semantic_fallback(text)

    if not skill_results:
        print("[ResumeParser] No recognizable skills found in resume.")
        return

    # Normalise weights relative to the highest-confidence skill
    max_confidence = max(r["confidence"] for r in skill_results)

    for entry in skill_results:
        skill_name: str = entry["skill"]
        confidence: float = entry["confidence"]
        normalized_weight: float = confidence / max_confidence if max_confidence > 0 else 0.0

        existing = (
            db.query(SkillWeight)
            .filter(
                SkillWeight.user_id == user_id,
                SkillWeight.skill_name == skill_name,
                SkillWeight.source == "resume",
            )
            .first()
        )

        if existing:
            existing.weight = normalized_weight
            existing.confidence = confidence
            print(f"[ResumeParser] Updated existing SkillWeight for {skill_name}")
        else:
            db.add(
                SkillWeight(
                    user_id=user_id,
                    skill_name=skill_name,
                    weight=normalized_weight,
                    confidence=confidence,
                    source="resume",
                )
            )
            print(f"[ResumeParser] Inserted new SkillWeight for {skill_name}")

    db.commit()
    print("[ResumeParser] SkillWeights committed. Running synthesis...")

    try:
        synthesize_all_skills_for_user(user_id, db)
    except Exception as e:
        print(f"[ResumeParser] Non-fatal error during synthesis: {e}")

    print("[ResumeParser] Ingestion pipeline complete.")
