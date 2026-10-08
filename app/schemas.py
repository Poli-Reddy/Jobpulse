from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class NormalizedJob(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    source: str
    source_job_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    company_name: str = Field(min_length=1, max_length=255)
    company_domain: str | None = None
    location: str = Field(default="Unknown", min_length=1, max_length=255)
    remote: bool = False
    description: str = ""
    job_url: HttpUrl
    employment_type: str | None = None
    level: str | None = None
    salary_min: float | None = Field(default=None, ge=0)
    salary_max: float | None = Field(default=None, ge=0)
    salary_currency: str | None = Field(default=None, max_length=10)
    salary_period: str | None = Field(default=None, max_length=30)
    published_at: datetime | None = None
    skills: list[str] = Field(default_factory=list)

    @field_validator("source")
    @classmethod
    def recognized_source(cls, value: str) -> str:
        value = value.casefold().strip()
        if value not in {"jobicy", "arbeitnow"}:
            raise ValueError("source is not recognized")
        return value

    @field_validator("source_job_id", "title", "company_name", "location")
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("value must not be blank")
        return value.strip()

    @model_validator(mode="after")
    def valid_salary_range(self):
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_max < self.salary_min
        ):
            raise ValueError("salary_max must be greater than or equal to salary_min")
        return self


class IngestionResult(BaseModel):
    source: str
    records_received: int
    records_inserted: int
    records_updated: int
    records_rejected: int
    duplicates: int
    error: str | None = None
