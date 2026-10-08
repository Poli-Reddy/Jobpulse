import hashlib
import json
import re
from datetime import datetime
from typing import Any

from bs4 import BeautifulSoup
from dateutil import parser as dateparser

from app.schemas import NormalizedJob

SKILL_PATTERNS: dict[str, tuple[str, ...]] = {
    "Python": (r"python(?:\s*3(?:\.\w+)?)?",),
    "SQL": (r"sql",),
    "R": (r"r",),
    "AWS": (r"aws",),
    "Azure": (r"azure",),
    "GCP": (r"gcp", r"google cloud"),
    "Docker": (r"docker",),
    "Kubernetes": (r"kubernetes", r"k8s"),
    "Airflow": (r"airflow",),
    "dbt": (r"dbt",),
    "Spark": (r"spark",),
    "Hadoop": (r"hadoop",),
    "Pandas": (r"pandas",),
    "NumPy": (r"numpy",),
    "PostgreSQL": (r"postgres(?:ql)?",),
    "MySQL": (r"mysql",),
    "MongoDB": (r"mongodb",),
    "Snowflake": (r"snowflake",),
    "Databricks": (r"databricks",),
    "Power BI": (r"power\s+bi",),
    "Tableau": (r"tableau",),
    "FastAPI": (r"fastapi",),
    "Java": (r"java",),
    "JavaScript": (r"javascript", r"js"),
    "TypeScript": (r"typescript", r"ts"),
    "React": (r"react",),
    "Node.js": (r"node(?:\.js)?",),
    "Kafka": (r"kafka",),
    "Terraform": (r"terraform",),
    "Git": (r"git",),
}

SKILL_CATEGORIES = {
    "Python": "Programming",
    "SQL": "Data",
    "R": "Programming",
    "AWS": "Cloud",
    "Azure": "Cloud",
    "GCP": "Cloud",
    "Docker": "DevOps",
    "Kubernetes": "DevOps",
    "Airflow": "Data Engineering",
    "dbt": "Data Engineering",
    "Spark": "Big Data",
    "Hadoop": "Big Data",
    "Pandas": "Data",
    "NumPy": "Data",
    "PostgreSQL": "Database",
    "MySQL": "Database",
    "MongoDB": "Database",
    "Snowflake": "Data Warehouse",
    "Databricks": "Data Platform",
    "Power BI": "BI",
    "Tableau": "BI",
    "FastAPI": "Backend",
    "Java": "Programming",
    "JavaScript": "Programming",
    "TypeScript": "Programming",
    "React": "Frontend",
    "Node.js": "Backend",
    "Kafka": "Streaming",
    "Terraform": "DevOps",
    "Git": "Tools",
}


def clean_html(text: str) -> str:
    return re.sub(r"\s+", " ", BeautifulSoup(text or "", "html.parser").get_text(" ")).strip()


def norm_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").casefold()).strip()


def normalize_title(title: str) -> str:
    return re.sub(r"\s+", " ", (title or "").strip())


def normalize_location(location: str) -> str:
    normalized = re.sub(r"\s+", " ", (location or "").strip())
    return re.sub(r"\bBangalore\b", "Bengaluru", normalized, flags=re.IGNORECASE)


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def deterministic_job_id(source: str, payload: dict[str, Any]) -> str:
    """Use a stable source identity when available, otherwise hash conservative job fields."""
    source_id = payload.get("id") or payload.get("slug")
    if source_id:
        return str(source_id).strip()
    url = payload.get("url") or payload.get("jobUrl")
    if url:
        identity = {"source": source.casefold(), "url": str(url).strip().casefold()}
    else:
        identity = {
            "source": source.casefold(),
            "title": norm_key(str(payload.get("jobTitle") or payload.get("title") or "")),
            "company": norm_key(
                str(payload.get("companyName") or payload.get("company_name") or "")
            ),
            "location": norm_key(
                str(payload.get("jobGeo") or payload.get("location") or "")
            ),
        }
    if not identity.get("url") and not (identity.get("title") and identity.get("company")):
        raise ValueError("record has no stable ID or sufficient fallback identity fields")
    encoded = json.dumps(identity, sort_keys=True, separators=(",", ":"))
    return f"fallback:{sha256(encoded)}"


def extract_skills(text: str) -> list[str]:
    normalized = (text or "").casefold()
    found = set()
    for skill, aliases in SKILL_PATTERNS.items():
        for alias in aliases:
            if re.search(rf"(?<![a-z0-9])(?:{alias})(?![a-z0-9])", normalized):
                found.add(skill)
                break
    return sorted(found, key=str.casefold)


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return dateparser.parse(str(value))
    except (TypeError, ValueError, OverflowError):
        return None


def normalize_jobicy(x: dict[str, Any]) -> NormalizedJob:
    description = clean_html(x.get("jobDescription") or x.get("jobExcerpt") or "")
    title = normalize_title(str(x.get("jobTitle") or ""))
    company = re.sub(r"\s+", " ", str(x.get("companyName") or "")).strip()
    geo = normalize_location(str(x.get("jobGeo") or "Unknown"))
    job_types = x.get("jobType") or []
    if isinstance(job_types, str):
        job_types = [job_types]
    return NormalizedJob(
        source="jobicy",
        source_job_id=deterministic_job_id("jobicy", x),
        title=title,
        company_name=company,
        location=geo,
        remote=True,
        description=description,
        job_url=x.get("url"),
        employment_type=", ".join(map(str, job_types)) or None,
        level=x.get("jobLevel"),
        salary_min=x.get("salaryMin"),
        salary_max=x.get("salaryMax"),
        salary_currency=x.get("salaryCurrency"),
        salary_period=x.get("salaryPeriod"),
        published_at=parse_dt(x.get("pubDate")),
        skills=extract_skills(description + " " + str(x.get("jobExcerpt") or "")),
    )


def normalize_arbeitnow(x: dict[str, Any]) -> NormalizedJob:
    description = clean_html(x.get("description") or "")
    raw_location = re.sub(r"\s+", " ", str(x.get("location") or "Remote")).strip()
    location = normalize_location(raw_location)
    created_at = parse_dt(x.get("created_at") or x.get("createdAt"))
    tags = x.get("tags") or []
    if isinstance(tags, str):
        tags = [tags]
    title = normalize_title(str(x.get("title") or ""))
    company = re.sub(r"\s+", " ", str(x.get("company_name") or "")).strip()
    remote = raw_location.casefold() in {"remote", "anywhere", "worldwide"}
    return NormalizedJob(
        source="arbeitnow",
        source_job_id=deterministic_job_id("arbeitnow", x),
        title=title,
        company_name=company,
        company_domain=x.get("company_url"),
        location=location,
        remote=remote,
        description=description,
        job_url=x.get("url"),
        employment_type=x.get("employment_type") or x.get("job_type"),
        level=None,
        salary_min=x.get("salary_min"),
        salary_max=x.get("salary_max"),
        salary_currency=x.get("salary_currency") or x.get("currency"),
        salary_period=x.get("salary_period"),
        published_at=created_at,
        skills=extract_skills(description + " " + " ".join(map(str, tags)) + " " + title),
    )
