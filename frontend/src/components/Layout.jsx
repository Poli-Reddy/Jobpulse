import { NavLink, Outlet } from "react-router-dom";

const links = [
  { to: "/", label: "Overview", icon: "◫", end: true },
  { to: "/jobs", label: "Jobs", icon: "▤" },
  { to: "/skills", label: "Skills", icon: "✳" },
  { to: "/companies", label: "Companies", icon: "▦" },
  { to: "/locations", label: "Locations", icon: "⌖" },
  { to: "/salary", label: "Salary", icon: "↗" },
  { to: "/pipeline", label: "Pipeline health", icon: "◉" },
];

export default function Layout() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <NavLink to="/" className="brand">
          <span className="brand-mark">J</span>
          <span>JobPulse<small>MARKET INTELLIGENCE</small></span>
        </NavLink>
        <div className="nav-section-label">WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          {links.map(({ to, label, icon, end }) => (
            <NavLink key={to} to={to} end={end} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
              <span className="nav-icon" aria-hidden="true">{icon}</span>{label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="live-dot" /> Connected to JobPulse API
        </div>
      </aside>
      <main className="main-area">
        <header className="topbar">
          <span>Job-market intelligence</span>
          <span className="topbar-tag">LIVE DATA</span>
        </header>
        <div className="content-area"><Outlet /></div>
      </main>
    </div>
  );
}
