const baseUrl = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace(
  /\/$/,
  "",
);

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      headers: { Accept: "application/json", ...options.headers },
      ...options,
    });
  } catch {
    throw new Error("Unable to reach the JobPulse API. Please try again later.");
  }

  if (!response.ok) {
    let message = `The API returned an error (${response.status}).`;
    try {
      const body = await response.json();
      message = body?.detail?.message || body?.detail || message;
    } catch {
      // Keep the useful status message when the server response is not JSON.
    }
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return response.json();
}

function withQuery(path, params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      query.set(key, String(value));
    }
  });
  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
}

export const api = {
  getHealth: () => request("/health"),
  getJobs: (params) => request(withQuery("/jobs", params)),
  getJob: (id) => request(`/jobs/${encodeURIComponent(id)}`),
  getCompanies: (params) => request(withQuery("/companies", params)),
  getSkills: (params) => request(withQuery("/skills", params)),
  getLocations: (params) => request(withQuery("/locations", params)),
  getSkillAnalytics: (limit = 10) =>
    request(withQuery("/analytics/skills", { limit })),
  getSkillGrowth: (limit = 100) =>
    request(withQuery("/analytics/skills/growth", { limit })),
  getCompanyAnalytics: (limit = 10) =>
    request(withQuery("/analytics/companies", { limit })),
  getLocationAnalytics: (limit = 10) =>
    request(withQuery("/analytics/locations", { limit })),
  getSalaryAnalytics: () => request("/analytics/salary"),
  getJobsTrend: (limit = 90) =>
    request(withQuery("/analytics/jobs/trend", { limit })),
  getOverview: () => request("/analytics/overview"),
  getPipelineStatus: () => request("/pipeline/status"),
  getSourceStatus: () => request("/sources/status"),
};
