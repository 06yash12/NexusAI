import {
  FolderKanban, ShieldCheck, Database,
  MessageSquare, LayoutDashboard, Lightbulb, Trash2, Plus, FileBarChart,
  Sun, Moon
} from "lucide-react";

export default function Sidebar({
  projects,
  activeProject,
  onSelect,
  onCreate,
  onDeleteProject,
  activeView,
  onSelectView,
  theme = "light",
  onToggleTheme
}) {
  return (
    <aside className="sidebar">
      {/* Brand Header: Logo and Name strictly parallel, matching exact branding */}
      <div className="brand">
        <div className="brand-logo-container">
          <img 
            src="/n_icon.png" 
            alt="NEXUS AI Logo" 
            className="brand-icon-img"
          />
        </div>
        <div className="brand-divider"></div>
        <div className="brand-text">
          <b className="brand-title">NEXUS AI</b>
          <span className="brand-subtitle">ENTERPRISE BI</span>
        </div>
      </div>

      {/* Main View Navigation Tabs */}
      <div className="nav-label">PLATFORM VIEWS</div>
      <div className="views-nav">
        <button
          className={`nav-tab-btn ${activeView === "chat" ? "active" : ""}`}
          onClick={() => onSelectView("chat")}
        >
          <MessageSquare size={16} />
          <span>AI Query &amp; Chat</span>
        </button>

        <button
          className={`nav-tab-btn ${activeView === "dashboard" ? "active" : ""}`}
          onClick={() => onSelectView("dashboard")}
        >
          <LayoutDashboard size={16} />
          <span>BI Dashboard</span>
        </button>

        <button
          className={`nav-tab-btn ${activeView === "insights" ? "active" : ""}`}
          onClick={() => onSelectView("insights")}
        >
          <Lightbulb size={16} />
          <span>Strategic Insights</span>
        </button>

        <button
          className={`nav-tab-btn ${activeView === "reports" ? "active" : ""}`}
          onClick={() => onSelectView("reports")}
        >
          <FileBarChart size={16} />
          <span>Reports &amp; Export</span>
        </button>
      </div>

      {/* Workspaces Section */}
      <div className="workspaces-header">
        <span className="nav-label">WORKSPACES</span>
        <button className="btn-add-project" onClick={onCreate} title="Create Workspace">
          <Plus size={14} />
        </button>
      </div>

      <div className="project-list">
        {projects.length === 0 ? (
          <div className="no-projects-hint">No workspaces yet.</div>
        ) : (
          projects.map(p => (
            <div
              key={p.id}
              className={`project-link-wrapper ${activeProject?.id === p.id ? "active" : ""}`}
            >
              <button
                className="project-link"
                onClick={() => onSelect(p)}
                title={p.name}
              >
                <FolderKanban size={15} />
                <span>{p.name}</span>
              </button>
              {projects.length > 1 && (
                <button
                  className="btn-delete-proj"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (window.confirm(`Delete workspace "${p.name}" and all its datasets?`)) {
                      onDeleteProject(p.id);
                    }
                  }}
                  title="Delete workspace"
                >
                  <Trash2 size={13} />
                </button>
              )}
            </div>
          ))
        )}
      </div>

      {/* Theme Toggle Button */}
      <div className="sidebar-theme-wrap">
        <button
          className="theme-toggle-btn"
          onClick={onToggleTheme}
          title={`Switch to ${theme === "light" ? "Dark" : "Light"} mode`}
        >
          {theme === "light" ? (
            <>
              <Moon size={15} />
              <span>Dark Mode</span>
            </>
          ) : (
            <>
              <Sun size={15} />
              <span>Light Mode</span>
            </>
          )}
        </button>
      </div>

      {/* Footer System Badges */}
      <div className="sidebar-bottom">
        <div>
          <Database size={14} className="text-blue" />
          <span>Local DuckDB Storage</span>
        </div>
        <div>
          <ShieldCheck size={14} className="text-emerald" />
          <span>Local Qwen3 &amp; Nomic AI</span>
        </div>
      </div>
    </aside>
  );
}
