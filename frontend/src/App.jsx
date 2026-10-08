import { Component } from "react";
import { Route, Routes } from "react-router-dom";
import Layout from "./components/Layout.jsx";
import {
  CompaniesPage,
  DashboardPage,
  JobDetailsPage,
  JobsPage,
  LocationsPage,
  NotFoundPage,
  PipelinePage,
  SalaryPage,
  SkillsPage,
} from "./pages.jsx";

class ApplicationErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { failed: false };
  }

  static getDerivedStateFromError() {
    return { failed: true };
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="fatal-error">
          <h1>JobPulse could not display this page.</h1>
          <p>Refresh the page or return to the dashboard.</p>
          <a href="/">Return to overview</a>
        </main>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <ApplicationErrorBoundary>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<DashboardPage />} />
          <Route path="jobs" element={<JobsPage />} />
          <Route path="jobs/:id" element={<JobDetailsPage />} />
          <Route path="skills" element={<SkillsPage />} />
          <Route path="companies" element={<CompaniesPage />} />
          <Route path="locations" element={<LocationsPage />} />
          <Route path="salary" element={<SalaryPage />} />
          <Route path="pipeline" element={<PipelinePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Route>
      </Routes>
    </ApplicationErrorBoundary>
  );
}
