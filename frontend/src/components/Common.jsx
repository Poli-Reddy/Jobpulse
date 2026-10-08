import React from "react";
import { Link } from "react-router-dom";

export function useApiData(loader) {
  const [state, setState] = React.useState({
    data: null,
    loading: true,
    error: "",
  });

  React.useEffect(() => {
    let current = true;
    setState({ data: null, loading: true, error: "" });
    loader()
      .then((data) => {
        if (current) setState({ data, loading: false, error: "" });
      })
      .catch((error) => {
        if (current) {
          setState({
            data: null,
            loading: false,
            error: error.message || "Unable to load JobPulse data.",
          });
        }
      });
    return () => {
      current = false;
    };
  }, [loader]);

  return state;
}

export function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p className="muted">{description}</p>}
      </div>
      {action}
    </div>
  );
}

export function Panel({ title, subtitle, action, children, className = "" }) {
  return (
    <section className={`panel ${className}`}>
      {(title || subtitle || action) && (
        <header className="panel-header">
          <div>
            {title && <h2>{title}</h2>}
            {subtitle && <p className="muted">{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}

export function LoadingState({ label = "Loading data..." }) {
  return (
    <div className="state-card" role="status">
      <span className="spinner" aria-hidden="true" />
      {label}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="state-card error-state" role="alert">
      <strong>Unable to load JobPulse data.</strong>
      <span>{message || "Please try again later."}</span>
      {onRetry && (
        <button className="button button-secondary" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ children = "No data available yet." }) {
  return <div className="empty-state">{children}</div>;
}

export function StatCard({ label, value, detail, icon }) {
  return (
    <article className="stat-card">
      <div className="stat-top">
        <span className="stat-icon" aria-hidden="true">{icon}</span>
        <span className="stat-label">{label}</span>
      </div>
      <strong className="stat-value">{value ?? "—"}</strong>
      {detail && <span className="stat-detail">{detail}</span>}
    </article>
  );
}

export function StatusBadge({ value }) {
  const normalized = String(value || "UNKNOWN").toLowerCase();
  return <span className={`status-badge status-${normalized}`}>{value || "Unknown"}</span>;
}

export function Pagination({ page, pageSize, total, onPageChange }) {
  const pages = Math.max(1, Math.ceil(total / pageSize));
  return (
    <div className="pagination">
      <span>
        {total === 0 ? "0 results" : `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, total)} of ${total}`}
      </span>
      <div className="pagination-actions">
        <button
          className="button button-secondary"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
        >
          Previous
        </button>
        <span>Page {page} of {pages}</span>
        <button
          className="button button-secondary"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
        >
          Next
        </button>
      </div>
    </div>
  );
}

export function DataTable({ columns, rows, rowKey, onRowClick }) {
  if (!rows?.length) return <EmptyState>No data available yet.</EmptyState>;
  return (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>{columns.map((column) => <th key={column.key}>{column.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr
              key={rowKey ? rowKey(row) : row.id ?? JSON.stringify(row)}
              className={onRowClick ? "clickable-row" : ""}
              onClick={onRowClick ? () => onRowClick(row) : undefined}
            >
              {columns.map((column) => (
                <td key={column.key}>{column.render ? column.render(row) : row[column.key] ?? "—"}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function BarList({ items, labelKey, valueKey, valueLabel = "jobs" }) {
  if (!items?.length) return <EmptyState>No data available yet.</EmptyState>;
  const maximum = Math.max(1, ...items.map((item) => Number(item[valueKey]) || 0));
  return (
    <div className="bar-list">
      {items.map((item, index) => {
        const value = Number(item[valueKey]) || 0;
        return (
          <div className="bar-item" key={`${item[labelKey]}-${index}`}>
            <div className="bar-label-row">
              <span title={item[labelKey]}>{item[labelKey]}</span>
              <strong>{value.toLocaleString()} <small>{valueLabel}</small></strong>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${Math.max(value ? 3 : 0, value / maximum * 100)}%` }} />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function TrendChart({ items }) {
  if (!items?.length) {
    return (
      <EmptyState>
        No data available yet. Run the ingestion pipeline to populate the dashboard.
      </EmptyState>
    );
  }
  const width = 760;
  const height = 190;
  const padding = 24;
  const values = items.map((item) => Number(item.jobs_first_seen) || 0);
  const max = Math.max(1, ...values);
  const points = values.map((value, index) => {
    const x = padding + (index / Math.max(1, values.length - 1)) * (width - padding * 2);
    const y = height - padding - (value / max) * (height - padding * 2);
    return `${x},${y}`;
  }).join(" ");
  const first = items[0]?.day;
  const last = items.at(-1)?.day;
  return (
    <div className="trend-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Jobs first seen over time">
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} className="chart-axis" />
        <polyline points={points} className="chart-line" />
        {values.map((value, index) => {
          const [x, y] = points.split(" ")[index].split(",");
          return <circle key={index} cx={x} cy={y} r="3" className="chart-dot"><title>{value} jobs</title></circle>;
        })}
      </svg>
      <div className="chart-foot"><span>{formatDate(first)}</span><span>{formatDate(last)}</span></div>
    </div>
  );
}

export function JobLink({ job, children }) {
  return <Link to={`/jobs/${job.id}`} onClick={(event) => event.stopPropagation()}>{children || job.title}</Link>;
}

export function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? String(value)
    : date.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

export function formatSalary(job) {
  if (job.salary_min == null && job.salary_max == null) return "Not provided";
  const currency = job.salary_currency || "";
  const amount = [job.salary_min, job.salary_max]
    .filter((value) => value != null)
    .map((value) => Number(value).toLocaleString())
    .join(" – ");
  return `${currency} ${amount}${job.salary_period ? ` / ${job.salary_period}` : ""}`.trim();
}

export function TagList({ items }) {
  return items?.length
    ? <div className="tag-list">{items.map((item) => <span className="tag" key={item}>{item}</span>)}</div>
    : <span className="muted">—</span>;
}
