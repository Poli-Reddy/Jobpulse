import pytest
from pydantic import ValidationError

from app.normalization import (
    clean_html,
    deterministic_job_id,
    extract_skills,
    norm_key,
    normalize_arbeitnow,
    normalize_location,
    normalize_title,
)


def test_clean_html():
    assert clean_html("<p>Hello&nbsp; world</p>") == "Hello world"


def test_skill_extraction_is_canonical_and_uses_token_boundaries():
    skills = extract_skills("Python python PYTHON Python 3 Postgres PostgreSQL")
    assert skills.count("Python") == 1
    assert skills.count("PostgreSQL") == 1
    assert extract_skills("programmer, library, runtime") == []
    assert extract_skills("R, RPG, Rust") == ["R"]


def test_norm_key():
    assert norm_key(" ACME, Inc. ") == "acme inc"


def test_titles_are_whitespace_normalized_without_merging_levels():
    assert normalize_title("  Data   Engineer ") == "Data Engineer"
    assert normalize_title("Senior Data Engineer") != normalize_title("Data Engineer")


def test_location_aliases_are_normalized_conservatively():
    assert normalize_location("Bangalore, India") == "Bengaluru, India"
    assert normalize_location("Bengaluru, India") == "Bengaluru, India"


def test_company_normalization_does_not_strip_company_suffixes():
    assert norm_key(" ACME, INC ") == norm_key("Acme Inc.")
    assert norm_key("Acme Inc.") != norm_key("Acme Labs")


def test_job_fallback_identity_is_deterministic():
    payload = {
        "title": "Data Engineer",
        "company_name": "Acme",
        "location": "Bengaluru",
        "url": "https://example.org/jobs/123",
    }
    assert deterministic_job_id("arbeitnow", payload) == deterministic_job_id(
        "arbeitnow", payload
    )


def test_invalid_salary_is_rejected():
    with pytest.raises(ValidationError):
        normalize_arbeitnow(
            {
                "id": "job-1",
                "title": "Engineer",
                "company_name": "Acme",
                "url": "https://example.org/jobs/1",
                "salary_min": 200,
                "salary_max": 100,
            }
        )
