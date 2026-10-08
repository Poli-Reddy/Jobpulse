import React, { useCallback, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "./services/api.js";
import {
  BarList,
  DataTable,
  EmptyState,
  ErrorState,
  formatDate,
  formatSalary,
  LoadingState,
  PageHeading,
  Pagination,
  Panel,
  StatCard,
  StatusBadge,
  TagList,
  TrendChart,
  useApiData,
} from "./components/Common.jsx";

function useRefreshable(loader) {
  const [refresh, setRefresh] = useState(0);
  const stableLoader = useCallback(() => loader(), [loader, refresh]);
  const state = useApiData(stableLoader);
  return { ...state, retry: () => setRefresh((value) => value + 1) };
}

export function DashboardPage() {
  const load = useCallback(() => Promise.all([
    api.getOverview(),
    api.getJobsTrend(90),
    api.getSkillAnalytics(8),
    api.getCompanyAnalytics(8),
    api.getLocationAnalytics(8),
  ]), []);
  const { data, loading, error, retry } = useRefreshable(load);

  return (
    <>
      <PageHeading
        eyebrow="MARKET OVERVIEW"
        title="Job market at a glance"
        description="A live view of listings collected from connected public sources."
      />
      {loading ? <LoadingState label="Loading dashboard..." /> : error ? <ErrorState message={error} onRetry={retry} /> : (
        <>
          <div className="stats-grid">
            <StatCard label="Active jobs" value={data[0].active_jobs} detail="Currently open listings" icon="▤" />
            <StatCard label="New jobs" value={data[0].new_jobs} detail="New in the latest observations" icon="✦" />
            <StatCard label="Companies hiring" value={data[0].companies_hiring} detail="With open listings" icon="▦" />
            <StatCard label="Tracked skills" value={data[0].tracked_skills} detail="In the skill catalogue" icon="✳" />
            <StatCard label="Sources" value={data[0].sources_succeeded} detail="Recently successful" icon="⌁" />
            <StatCard label="Last pipeline run" value={data[0].last_pipeline_run ? formatDate(data[0].last_pipeline_run) : "Not run"} detail="Most recent recorded run" icon="◷" />
          </div>
          <div className="dashboard-grid">
            <Panel title="Jobs over time" subtitle="Listings by first-seen date" className="panel-wide">
              <TrendChart items={data[1]} />
            </Panel>
            <Panel title="Top skills" subtitle="Jobs mentioning each skill">
              <BarList items={data[2]} labelKey="skill" valueKey="job_count" />
            </Panel>
            <Panel title="Top companies" subtitle="Current hiring activity">
              <BarList items={data[3]} labelKey="company" valueKey="active_jobs" />
            </Panel>
            <Panel title="Top locations" subtitle="Listings by normalized location">
              <BarList items={data[4]} labelKey="location" valueKey="job_count" />
            </Panel>
          </div>
          {data[0].active_jobs === 0 && (
            <div className="notice">
              No data available yet. Run the ingestion pipeline to populate the dashboard.
            </div>
          )}
        </>
      )}
    </>
  );
}

const statusOptions = ["NEW", "ACTIVE", "UPDATED", "CLOSED", "REACTIVATED"];

export function JobsPage() {
  const [filters, setFilters] = useState({});
  const [draft, setDraft] = useState({});
  const [page, setPage] = useState(1);
  const load = useCallback(() => api.getJobs({ page, page_size: 25, ...filters }), [page, filters]);
  const { data, loading, error, retry } = useRefreshable(load);
  const changeFilter = (event) => setDraft((previous) => ({ ...previous, [event.target.name]: event.target.value }));
  const submit = (event) => {
    event.preventDefault();
    setPage(1);
    setFilters(draft);
  };

  return (
    <>
      <PageHeading eyebrow="OPPORTUNITY SEARCH" title="Job listings" description="Search and filter jobs stored in the JobPulse database." />
      <Panel className="filter-panel">
        <form className="filter-form" onSubmit={submit}>
          <label className="search-field">Search<input name="search" value={draft.search || ""} onChange={changeFilter} placeholder="Role, company, or description" /></label>
          <label>Company<input name="company" value={draft.company || ""} onChange={changeFilter} placeholder="Company name" /></label>
          <label>Location<input name="location" value={draft.location || ""} onChange={changeFilter} placeholder="City or region" /></label>
          <label>Skill<input name="skill" value={draft.skill || ""} onChange={changeFilter} placeholder="e.g. Python" /></label>
          <label>Source<select name="source" value={draft.source || ""} onChange={changeFilter}><option value="">All sources</option><option value="jobicy">Jobicy</option><option value="arbeitnow">Arbeitnow</option></select></label>
          <label>Status<select name="status" value={draft.status || ""} onChange={changeFilter}><option value="">All statuses</option>{statusOptions.map((status) => <option key={status}>{status}</option>)}</select></label>
          <label>Work mode<select name="remote_type" value={draft.remote_type || ""} onChange={changeFilter}><option value="">Any work mode</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="onsite">On-site</option></select></label>
          <button className="button button-primary" type="submit">Apply filters</button>
        </form>
      </Panel>
      <Panel title="Results" subtitle={data ? `${data.total.toLocaleString()} listings` : "Database-backed job listings"}>
        {loading ? <LoadingState label="Loading jobs..." /> : error ? <ErrorState message={error} onRetry={retry} /> : (
          <>
            <DataTable
              rows={data.items}
              columns={[
                { key: "title", label: "Job title", render: (job) => <Link to={`/jobs/${job.id}`} className="job-title-link">{job.title}</Link> },
                { key: "company", label: "Company" },
                { key: "location", label: "Location" },
                { key: "source", label: "Source", render: (job) => <span className="source-name">{job.source}</span> },
                { key: "status", label: "Status", render: (job) => <StatusBadge value={job.status} /> },
                { key: "first_seen_at", label: "First seen", render: (job) => formatDate(job.first_seen_at) },
              ]}
            />
            <Pagination page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
          </>
        )}
      </Panel>
    </>
  );
}

export function JobDetailsPage() {
  const { id } = useParams();
  const load = useCallback(() => api.getJob(id), [id]);
  const { data, loading, error, retry } = useRefreshable(load);
  if (loading) return <LoadingState label="Loading job details..." />;
  if (error) return <ErrorState message={error} onRetry={retry} />;
  return (
    <>
      <div className="back-link"><Link to="/jobs">← Back to jobs</Link></div>
      <PageHeading eyebrow={`${data.source} LISTING`} title={data.title} description={`${data.company} · ${data.location}`} action={<StatusBadge value={data.status} />} />
      <div className="detail-grid">
        <Panel title="Job description" className="detail-main">
          {data.description ? <div className="job-description">{data.description}</div> : <EmptyState>Description was not provided by the source.</EmptyState>}
        </Panel>
        <Panel title="Listing information">
          <dl className="detail-list">
            <dt>Company</dt><dd>{data.company}</dd>
            {data.company_domain && <><dt>Company domain</dt><dd>{data.company_domain}</dd></>}
            <dt>Location</dt><dd>{data.location}{data.remote ? " · Remote" : ""}</dd>
            <dt>Employment</dt><dd>{data.employment_type || "Not provided"}</dd>
            <dt>Level</dt><dd>{data.level || "Not provided"}</dd>
            <dt>Salary</dt><dd>{formatSalary(data)}</dd>
            <dt>Published</dt><dd>{formatDate(data.published_at)}</dd>
            <dt>First seen</dt><dd>{formatDate(data.first_seen_at)}</dd>
            <dt>Last seen</dt><dd>{formatDate(data.last_seen_at)}</dd>
            <dt>Last updated</dt><dd>{formatDate(data.updated_at)}</dd>
          </dl>
          <a className="button button-primary source-link" href={data.job_url} target="_blank" rel="noreferrer">Open original listing ↗</a>
        </Panel>
        <Panel title="Skills">
          <TagList items={data.skills} />
        </Panel>
      </div>
    </>
  );
}

export function SkillsPage() {
  const load = useCallback(() => Promise.all([
    api.getSkills({ page: 1, page_size: 100 }),
    api.getSkillAnalytics(10),
    api.getSkillGrowth(100),
  ]), []);
  const { data, loading, error, retry } = useRefreshable(load);
  return (
    <>
      <PageHeading eyebrow="CAPABILITY SIGNALS" title="Skills analytics" description="Skill demand and monthly observations from collected job listings." />
      {loading ? <LoadingState label="Loading skills..." /> : error ? <ErrorState message={error} onRetry={retry} /> : (
        <div className="dashboard-grid">
          <Panel title="Top skills" subtitle="Job count from analytics models" className="panel-wide">
            <BarList items={data[1]} labelKey="skill" valueKey="job_count" />
          </Panel>
          <Panel title="Tracked catalogue" subtitle={`${data[0].total} skills in stored job records`}>
            <DataTable rows={data[0].items.slice(0, 12)} columns={[
              { key: "name", label: "Skill" },
              { key: "category", label: "Category" },
              { key: "job_count", label: "Jobs" },
            ]} />
          </Panel>
          <Panel title="Monthly skill demand" subtitle="Based on listing publication dates" className="panel-wide">
            {new Set(data[2].map((row) => String(row.month).slice(0, 7))).size > 1 ? (
              <DataTable rows={data[2]} columns={[
                { key: "month", label: "Month", render: (row) => formatDate(row.month) },
                { key: "skill", label: "Skill" },
                { key: "job_count", label: "Jobs" },
              ]} />
            ) : <EmptyState>There is not enough historical data to show skill growth yet.</EmptyState>}
          </Panel>
        </div>
      )}
    </>
  );
}

export function CompaniesPage() {
  const [page, setPage] = useState(1);
  const load = useCallback(() => api.getCompanies({ page, page_size: 25 }), [page]);
  const { data, loading, error, retry } = useRefreshable(load);
  return (
    <>
      <PageHeading eyebrow="HIRING ORGANIZATIONS" title="Companies" description="Organizations and active listings recorded from source data." />
      <Panel title="Companies" subtitle={data ? `${data.total} companies` : "Stored company records"}>
        {loading ? <LoadingState label="Loading companies..." /> : error ? <ErrorState message={error} onRetry={retry} /> : (
          <>
            <DataTable rows={data.items} columns={[
              { key: "name", label: "Company" },
              { key: "active_jobs", label: "Active jobs" },
              { key: "new_jobs", label: "New jobs" },
              { key: "location_count", label: "Locations" },
              { key: "top_skills", label: "Top skills", render: (row) => <TagList items={row.top_skills} /> },
            ]} />
            <Pagination page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
          </>
        )}
      </Panel>
    </>
  );
}

export function LocationsPage() {
  const [page, setPage] = useState(1);
  const load = useCallback(() => api.getLocations({ page, page_size: 25 }), [page]);
  const { data, loading, error, retry } = useRefreshable(load);
  return (
    <>
      <PageHeading eyebrow="GEOGRAPHIC DEMAND" title="Locations" description="Normalized locations and work modes observed in job listings." />
      <Panel title="Location demand" subtitle={data ? `${data.total} locations` : "Stored location records"}>
        {loading ? <LoadingState label="Loading locations..." /> : error ? <ErrorState message={error} onRetry={retry} /> : (
          <>
            <DataTable rows={data.items} columns={[
              { key: "name", label: "Location" },
              { key: "job_count", label: "Jobs" },
              { key: "top_skills", label: "Top skills", render: (row) => <TagList items={row.top_skills} /> },
              { key: "remote", label: "Work mode", render: (row) => row.remote ? "Remote" : /hybrid/i.test(row.raw_location || "") ? "Hybrid" : "Not remote" },
            ]} />
            <Pagination page={page} pageSize={data.page_size} total={data.total} onPageChange={setPage} />
          </>
        )}
      </Panel>
    </>
  );
}

export function SalaryPage() {
  const load = useCallback(() => api.getSalaryAnalytics(), []);
  const { data, loading, error, retry } = useRefreshable(load);
  return (
    <>
      <PageHeading eyebrow="COMPENSATION" title="Salary intelligence" description="Only salary amounts explicitly provided by source listings are included." />
      <Panel title="Reported salary data" subtitle="Grouped by currency and reporting period">
        {loading ? <LoadingState label="Loading salary analytics..." /> : error ? <ErrorState message={error} onRetry={retry} /> : data.length ? (
          <DataTable rows={data} columns={[
            { key: "currency", label: "Currency" },
            { key: "salary_period", label: "Period" },
            { key: "jobs_with_salary", label: "Listings" },
            { key: "avg_salary_min", label: "Average minimum", render: (row) => row.avg_salary_min == null ? "—" : Number(row.avg_salary_min).toLocaleString() },
            { key: "avg_salary_max", label: "Average maximum", render: (row) => row.avg_salary_max == null ? "—" : Number(row.avg_salary_max).toLocaleString() },
          ]} />
        ) : <EmptyState>Salary data is currently unavailable for the collected sources.</EmptyState>}
      </Panel>
    </>
  );
}

export function PipelinePage() {
  const load = useCallback(() => Promise.all([api.getPipelineStatus(), api.getSourceStatus()]), []);
  const { data, loading, error, retry } = useRefreshable(load);
  return (
    <>
      <PageHeading eyebrow="OPERATIONS" title="Pipeline health" description="Ingestion run metrics and per-source reliability." />
      {loading ? <LoadingState label="Loading pipeline status..." /> : error ? <ErrorState message={error} onRetry={retry} /> : (
        <>
          <Panel title="Latest pipeline run" subtitle={data[0].started_at ? formatDate(data[0].started_at) : "No pipeline run recorded"}>
            <div className="pipeline-status-row"><StatusBadge value={data[0].status} />{data[0].pipeline_name && <span>{data[0].pipeline_name}</span>}</div>
            {data[0].last_run === null && !data[0].started_at ? <EmptyState>No pipeline run recorded yet.</EmptyState> : (
              <div className="stats-grid pipeline-stats">
                <StatCard label="Execution time" value={data[0].execution_time_ms == null ? "—" : `${(data[0].execution_time_ms / 1000).toFixed(1)}s`} icon="◷" />
                <StatCard label="Received" value={data[0].records_received} icon="↓" />
                <StatCard label="Inserted" value={data[0].records_inserted} icon="＋" />
                <StatCard label="Updated" value={data[0].records_updated} icon="↻" />
                <StatCard label="Rejected" value={data[0].records_rejected} icon="!" />
                <StatCard label="Duplicates" value={data[0].duplicates} icon="⧉" />
              </div>
            )}
            {data[0].error_message && <div className="notice notice-error">{data[0].error_message}</div>}
          </Panel>
          <Panel title="Source health" subtitle="Latest result recorded for each configured source">
            <DataTable rows={data[1]} columns={[
              { key: "source", label: "Source" },
              { key: "status", label: "Status", render: (row) => <StatusBadge value={row.status} /> },
              { key: "last_run_at", label: "Last run", render: (row) => formatDate(row.last_run_at) },
              { key: "records_received", label: "Received" },
              { key: "records_inserted", label: "Inserted" },
              { key: "records_updated", label: "Updated" },
              { key: "records_rejected", label: "Rejected" },
              { key: "duplicates", label: "Duplicates" },
              { key: "error", label: "Last error", render: (row) => row.error || "—" },
            ]} />
          </Panel>
        </>
      )}
    </>
  );
}

export function NotFoundPage() {
  return <div className="not-found"><h1>Page not found</h1><Link to="/">Return to overview</Link></div>;
}
