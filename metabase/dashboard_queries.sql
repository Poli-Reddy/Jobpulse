-- Top skills
SELECT skill, job_count, active_job_count
FROM analytics.skill_demand
ORDER BY job_count DESC
LIMIT 20;

-- Hiring companies
SELECT company_name, active_jobs, job_count
FROM analytics.company_hiring
ORDER BY active_jobs DESC
LIMIT 20;

-- Hiring locations
SELECT location, active_jobs, job_count, remote_jobs
FROM analytics.location_demand
ORDER BY active_jobs DESC
LIMIT 20;

-- Daily trend of jobs first observed by the pipeline
SELECT day, jobs_first_seen
FROM analytics.daily_job_trend
ORDER BY day;

-- Source-reported salary grouped by currency and period (never combine unlike values)
SELECT currency, salary_period, avg_salary_min, avg_salary_max, jobs_with_salary
FROM analytics.salary_demand
ORDER BY jobs_with_salary DESC;
