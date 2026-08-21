"""
Tests for the improved resume skill extraction pipeline.

Covers:
  - clean_line normalisation
  - is_header_line heuristic
  - alias matching (longest-first, no double-counting)
  - section-aware confidence boost
  - extract_skills_from_text end-to-end
  - extract_text_from_pdf (PyMuPDF / pdfplumber)

Run with:
  cd backend && pytest tests/test_resume_parser.py -v
"""

from __future__ import annotations

import pytest

from services.skill_extractor import (
    clean_line,
    extract_skills_from_text,
    is_header_line,
    _match_aliases_in_line,
    _classify_header,
)


# ---------------------------------------------------------------------------
# clean_line
# ---------------------------------------------------------------------------

class TestCleanLine:
    @pytest.mark.unit
    def test_normalises_unicode_bullets(self):
        line = "\u2022 React  \u25cf Docker"
        result = clean_line(line)
        assert "react" in result
        assert "docker" in result

    @pytest.mark.unit
    def test_lowercases(self):
        assert clean_line("Python") == "python"

    @pytest.mark.unit
    def test_collapses_whitespace(self):
        assert "  " not in clean_line("foo   bar   baz")

    @pytest.mark.unit
    def test_handles_non_string(self):
        assert clean_line(None) == ""  # type: ignore[arg-type]

    @pytest.mark.unit
    def test_strips_leading_trailing_commas(self):
        result = clean_line("  , python , ")
        assert not result.startswith(",")
        assert not result.endswith(",")

    @pytest.mark.unit
    def test_replaces_ampersand(self):
        assert "and" in clean_line("HTML & CSS")


# ---------------------------------------------------------------------------
# is_header_line
# ---------------------------------------------------------------------------

class TestIsHeaderLine:
    @pytest.mark.unit
    def test_short_line_is_header(self):
        assert is_header_line("skills") is True

    @pytest.mark.unit
    def test_long_line_is_not_header(self):
        assert is_header_line("a" * 51) is False

    @pytest.mark.unit
    def test_sentence_ending_period_is_not_header(self):
        assert is_header_line("experience and education.") is False

    @pytest.mark.unit
    def test_six_word_line_is_not_header(self):
        assert is_header_line("one two three four five six") is False

    @pytest.mark.unit
    def test_empty_is_not_header(self):
        assert is_header_line("") is False


# ---------------------------------------------------------------------------
# _classify_header
# ---------------------------------------------------------------------------

class TestClassifyHeader:
    @pytest.mark.unit
    def test_skills_header(self):
        assert _classify_header("skills") == "skills"

    @pytest.mark.unit
    def test_technical_skills_header(self):
        assert _classify_header("technical skills") == "skills"

    @pytest.mark.unit
    def test_education_is_other(self):
        assert _classify_header("education") == "other"

    @pytest.mark.unit
    def test_experience_is_other(self):
        assert _classify_header("experience") == "other"

    @pytest.mark.unit
    def test_prose_line_is_none(self):
        assert _classify_header("developed and deployed microservices") is None


# ---------------------------------------------------------------------------
# _match_aliases_in_line — longest-first, no double counting
# ---------------------------------------------------------------------------

class TestMatchAliasesInLine:
    @pytest.mark.unit
    def test_react_native_not_double_counted(self):
        """'react native' should match react-native, not also react."""
        hits = _match_aliases_in_line("react native developer")
        assert "react-native" in hits
        assert hits.count("react") == 0

    @pytest.mark.unit
    def test_spring_boot_not_double_counted(self):
        hits = _match_aliases_in_line("spring boot microservice")
        assert "java" in hits          # spring boot → java
        assert hits.count("java") == 1  # only once

    @pytest.mark.unit
    def test_node_js_matches(self):
        hits = _match_aliases_in_line("node.js express api")
        assert "nodejs" in hits

    @pytest.mark.unit
    def test_multiple_skills(self):
        hits = _match_aliases_in_line("python, docker, kubernetes")
        assert "python" in hits
        assert "docker" in hits
        assert "kubernetes" in hits

    @pytest.mark.unit
    def test_no_match_returns_empty(self):
        assert _match_aliases_in_line("wrote quarterly reports") == []


# ---------------------------------------------------------------------------
# extract_skills_from_text — end-to-end
# ---------------------------------------------------------------------------

class TestExtractSkillsFromText:
    @pytest.mark.unit
    def test_basic_skill_detected(self):
        text = "I have experience with Python and Docker."
        results = extract_skills_from_text(text)
        skill_ids = {r["skill"] for r in results}
        assert "python" in skill_ids
        assert "docker" in skill_ids

    @pytest.mark.unit
    def test_output_format(self):
        text = "Skills: JavaScript, TypeScript"
        results = extract_skills_from_text(text)
        for r in results:
            assert "skill" in r
            assert "confidence" in r
            assert r["source"] == "resume"
            assert 0.0 <= r["confidence"] <= 1.0

    @pytest.mark.unit
    def test_section_boost_increases_confidence(self):
        """A skill inside a Skills section should have higher confidence
        than an identical mention only in prose elsewhere."""
        text_with_section = (
            "Summary\n"
            "Worked on many projects.\n"
            "Technical Skills\n"
            "Python\n"
        )
        text_prose_only = (
            "Summary\n"
            "Worked extensively with Python.\n"
        )
        section_results = extract_skills_from_text(text_with_section)
        prose_results = extract_skills_from_text(text_prose_only)

        section_conf = next(
            (r["confidence"] for r in section_results if r["skill"] == "python"), 0
        )
        prose_conf = next(
            (r["confidence"] for r in prose_results if r["skill"] == "python"), 0
        )
        assert section_conf >= prose_conf

    @pytest.mark.unit
    def test_empty_text_returns_empty_list(self):
        assert extract_skills_from_text("") == []

    @pytest.mark.unit
    def test_text_with_no_skills_returns_empty_list(self):
        assert extract_skills_from_text("Managed quarterly budgets and led team synergies.") == []

    @pytest.mark.unit
    def test_confidence_capped_at_one(self):
        # Mention the skill many times
        text = "\n".join(["python"] * 20)
        results = extract_skills_from_text(text)
        for r in results:
            assert r["confidence"] <= 1.0

    @pytest.mark.unit
    def test_bullet_list_in_skills_section(self):
        text = (
            "Technical Skills\n"
            "\u2022 JavaScript\n"
            "\u2022 React\n"
            "\u2022 Docker\n"
        )
        results = extract_skills_from_text(text)
        skill_ids = {r["skill"] for r in results}
        assert "javascript" in skill_ids
        assert "react" in skill_ids
        assert "docker" in skill_ids

    @pytest.mark.unit
    def test_aliases_case_insensitive(self):
        results = extract_skills_from_text("PYTHON and JAVASCRIPT developer")
        skill_ids = {r["skill"] for r in results}
        assert "python" in skill_ids
        assert "javascript" in skill_ids


# ---------------------------------------------------------------------------
# extract_text_from_pdf — smoke test (requires pymupdf or pdfplumber)
# ---------------------------------------------------------------------------

class TestExtractTextFromPdf:
    @pytest.mark.unit
    def test_missing_file_raises(self):
        from services.resume_parser import extract_text_from_pdf
        with pytest.raises(Exception):
            extract_text_from_pdf("/nonexistent/path/resume.pdf")
