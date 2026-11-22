import { useEffect, useState, useRef } from "react";
import {
  UploadCloud, BarChart3, Files, Table2, RefreshCw,
  Trash2, Eye, AlertCircle, CheckCircle2, Download, Loader2,
  ChevronDown, ChevronUp, Scissors
} from "lucide-react";
import Sidebar from "./components/Sidebar";
import ChatPanel from "./components/ChatPanel";
import DashboardView from "./components/DashboardView";
import InsightsView from "./components/InsightsView";
import ReportsView from "./components/ReportsView";
import DatasetPreviewModal from "./components/DatasetPreviewModal";
import LargeFileSplitModal from "./components/LargeFileSplitModal";
import { splitFileIntoChunks } from "./utils/fileChunker";
import { api, getError } from "./lib/api";

export default function App() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("nexus_theme") || "light";
  });
  const [projects, setProjects] = useState([]);
  const [active, setActive] = useState(null);
  const [activeView, setActiveView] = useState("chat");
  const [dashboard, setDashboard] = useState(null);
  const [datasets, setDatasets] = useState([]);
  const [insights, setInsights] = useState(null);
  const [messages, setMessages] = useState([]);
  const [chatMode, setChatMode] = useState("auto");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");
  const [previewData, setPreviewData] = useState(null);
  const [selectedTable, setSelectedTable] = useState(null);
  const [selectedYear, setSelectedYear] = useState(null);
  const [selectedRegion, setSelectedRegion] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedDepartment, setSelectedDepartment] = useState(null);
  const [selectedFacility, setSelectedFacility] = useState(null);
  const [selectedCity, setSelectedCity] = useState(null);
  const [selectedVisitType, setSelectedVisitType] = useState(null);
  // Uploaded Files panel minimize state
  const [isFilesCollapsed, setIsFilesCollapsed] = useState(false);
  // Multi-file selection state for AI query targeting
  const [selectedDatasetIds, setSelectedDatasetIds] = useState([]);
  // Multi-file upload state
  const [uploadQueue, setUploadQueue] = useState([]); // [{name, status, error, rawFile}]
  const [isDragOver, setIsDragOver] = useState(false);
  const [pendingSplitFile, setPendingSplitFile] = useState(null);
  const fileInputRef = useRef(null);

  // Synchronize theme to document body and persist
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("nexus_theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => (prev === "light" ? "dark" : "light"));
  };

  // Load projects list
  async function loadProjects() {
    try {
      const { data } = await api.get("/projects");
      setProjects(data);
      if (!active && data.length > 0) {
        setActive(data[0]);
      }
    } catch (e) {
      setNotice(getError(e));
    }
  }

  useEffect(() => {
    loadProjects();
  }, []);

  // When active workspace changes, reset project-specific filters and reload data
  useEffect(() => {
    if (!active) return;
    setSelectedYear(null);
    setSelectedTable(null);
    setSelectedRegion(null);
    setSelectedCategory(null);
    setSelectedDepartment(null);
    setSelectedFacility(null);
    setSelectedCity(null);
    setSelectedVisitType(null);
    setSelectedDatasetIds([]);
    refreshWorkspace(active.id, null, null, null, null, null, null, null, null);
  }, [active]);

  async function refreshWorkspace(
    projectId,
    tableFilter = selectedTable,
    yearFilter = selectedYear,
    regionFilter = selectedRegion,
    categoryFilter = selectedCategory,
    departmentFilter = selectedDepartment,
    facilityFilter = selectedFacility,
    cityFilter = selectedCity,
    visitTypeFilter = selectedVisitType
  ) {
    try {
      const params = [];
      if (tableFilter) params.push(`table=${encodeURIComponent(tableFilter)}`);
      if (yearFilter !== null && yearFilter !== undefined) params.push(`year=${encodeURIComponent(yearFilter)}`);
      if (regionFilter) params.push(`region=${encodeURIComponent(regionFilter)}`);
      if (categoryFilter) params.push(`category=${encodeURIComponent(categoryFilter)}`);
      if (departmentFilter) params.push(`department=${encodeURIComponent(departmentFilter)}`);
      if (facilityFilter) params.push(`facility=${encodeURIComponent(facilityFilter)}`);
      if (cityFilter) params.push(`city=${encodeURIComponent(cityFilter)}`);
      if (visitTypeFilter) params.push(`visit_type=${encodeURIComponent(visitTypeFilter)}`);
      const queryString = params.length > 0 ? `?${params.join("&")}` : "";

      const [dashRes, dataRes, convRes, insRes] = await Promise.all([
        api.get(`/projects/${projectId}/dashboard${queryString}`),
        api.get(`/projects/${projectId}/datasets`),
        api.get(`/projects/${projectId}/conversations`),
        api.get(`/projects/${projectId}/insights`).catch(() => ({ data: null }))
      ]);

      setDashboard(dashRes.data);
      setDatasets(dataRes.data);
      setInsights(insRes.data);

      // Reconstruct messages array from persistent conversations
      const historyMessages = [];
      for (const c of convRes.data) {
        historyMessages.push({ role: "user", text: c.question });
        historyMessages.push({
          role: "assistant",
          answer: c.answer,
          mode: c.mode,
          sql: c.sql_query,
          sources: c.sources || [],
          execution_time_ms: c.execution_time_ms
        });
      }
      setMessages(historyMessages);
    } catch (e) {
      setNotice(getError(e));
    }
  }

  async function createProject() {
    const name = window.prompt("Enter new workspace name (e.g. Q1 Retail Analytics):");
    if (!name?.trim()) return;
    try {
      const { data } = await api.post("/projects", { name: name.trim(), description: "" });
      setProjects(prev => [data, ...prev]);
      setActive(data);
      setNotice(`Created workspace "${data.name}".`);
    } catch (e) {
      setNotice(getError(e));
    }
  }

  async function deleteProject(projectId) {
    try {
      await api.delete(`/projects/${projectId}`);
      const remaining = projects.filter(p => p.id !== projectId);
      setProjects(remaining);
      if (active?.id === projectId) {
        setActive(remaining[0] || null);
      }
      setNotice("Workspace deleted.");
    } catch (e) {
      setNotice(getError(e));
    }
  }

  async function uploadBatch(fileList) {
    if (!fileList?.length || !active) return;

    // Initialize queue entries, preserving rawFile reference for split/retry actions
    const initial = fileList.map(f => ({ name: f.name, status: "pending", error: null, rawFile: f }));
    setUploadQueue(prev => [...prev, ...initial]);
    setBusy(true);
    setNotice("");

    let successCount = 0;
    let failCount = 0;

    for (let i = 0; i < fileList.length; i++) {
      const file = fileList[i];
      setUploadQueue(q => q.map(item => item.name === file.name && item.status === "pending" ? { ...item, status: "uploading" } : item));

      const formData = new FormData();
      formData.append("file", file);
      try {
        await api.post(`/projects/${active.id}/files`, formData, {
          headers: { "Content-Type": "multipart/form-data" }
        });
        setUploadQueue(q => q.map(item => item.name === file.name && item.status === "uploading" ? { ...item, status: "success" } : item));
        successCount++;
      } catch (err) {
        const errMsg = getError(err);
        setUploadQueue(q => q.map(item => item.name === file.name && item.status === "uploading" ? { ...item, status: "error", error: errMsg } : item));
        failCount++;
      }
    }

    await refreshWorkspace(active.id);
    setBusy(false);

    if (successCount > 0 && failCount === 0) {
      setNotice(`${successCount} file${successCount > 1 ? "s" : ""} ingested successfully.`);
      setTimeout(() => setUploadQueue([]), 6000);
    } else if (successCount > 0) {
      setNotice(`${successCount} uploaded, ${failCount} failed — see options below.`);
    } else {
      setNotice(`Upload encountered issues. Check file format or use the split option for files > 50MB.`);
    }
  }

  async function uploadFiles(files) {
    if (!files?.length || !active) return;
    const fileList = Array.from(files);

    // If any file exceeds standard 50MB, prompt user to split into parts
    const largeFile = fileList.find(f => f.size > 50 * 1024 * 1024);
    if (largeFile) {
      setPendingSplitFile(largeFile);
      // Ingest any remaining smaller files in this drop/selection
      const normalFiles = fileList.filter(f => f !== largeFile);
      if (normalFiles.length > 0) {
        uploadBatch(normalFiles);
      }
      return;
    }

    await uploadBatch(fileList);
  }

  async function handleSplitAndUploadFile(file, chunkSizeMb = 25) {
    if (!file || !active) return;
    setNotice(`Splitting "${file.name}" into ~${chunkSizeMb} MB parts...`);
    try {
      const parts = await splitFileIntoChunks(file, chunkSizeMb);
      setNotice(`Created ${parts.length} parts with preserved headers. Ingesting parts...`);
      await uploadBatch(parts);
    } catch (err) {
      setNotice(`Failed to split file: ${err.message}`);
    }
  }

  async function handleDirectUploadFile(file) {
    if (!file || !active) return;
    await uploadBatch([file]);
  }

  function handleFileInput(e) {
    uploadFiles(e.target.files);
    e.target.value = "";
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragOver(false);
    uploadFiles(e.dataTransfer.files);
  }

  function handleDragOver(e) {
    e.preventDefault();
    setIsDragOver(true);
  }

  function handleDragLeave() {
    setIsDragOver(false);
  }

  async function deleteDataset(datasetId, filename) {
    if (!window.confirm(`Delete dataset "${filename}"?`)) return;
    try {
      await api.delete(`/projects/${active.id}/datasets/${datasetId}`);
      await refreshWorkspace(active.id);
      setNotice(`Dataset "${filename}" removed.`);
    } catch (err) {
      setNotice(getError(err));
    }
  }

  async function previewDataset(datasetId) {
    try {
      const { data } = await api.get(`/projects/${active.id}/datasets/${datasetId}/preview?limit=25`);
      setPreviewData(data);
    } catch (err) {
      setNotice(getError(err));
    }
  }

  async function handleAsk(question, modeOverride = chatMode) {
    if (!active) return;
    setBusy(true);
    setNotice("");

    // Add user question to UI immediately
    setMessages(m => [...m, { role: "user", text: question }]);

    try {
      const payload = {
        question,
        mode: modeOverride
      };
      if (selectedDatasetIds.length > 0) {
        payload.selected_dataset_ids = selectedDatasetIds;
      }
      const { data } = await api.post(`/projects/${active.id}/chat`, payload);
      setMessages(m => [...m, { role: "assistant", ...data }]);
    } catch (err) {
      setMessages(m => [
        ...m,
        {
          role: "assistant",
          text: `Error processing request: ${getError(err)}`,
          sources: [],
          warnings: ["Operation failed."]
        }
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function handleNewChat() {
    if (!active) return;
    if (messages.length === 0) return;
    if (window.confirm("Clear current conversation history for this workspace?")) {
      try {
        await api.delete(`/projects/${active.id}/conversations`);
        setMessages([]);
        setNotice("Conversation history cleared.");
      } catch (err) {
        setNotice(getError(err));
      }
    }
  }

  const toggleDatasetSelection = (id) => {
    setSelectedDatasetIds(prev => {
      if (prev.includes(id)) {
        return prev.filter(x => x !== id);
      } else {
        return [...prev, id];
      }
    });
  };

  const selectAllDatasets = () => {
    setSelectedDatasetIds([]); // Empty means "All Datasets"
  };

  const getCleanDisplayName = (item) => {
    const raw = item.original_filename || item.filename || "Dataset";
    // Strip file extensions like .csv, .xlsx, .pdf, .docx
    return raw.replace(/\.(csv|xlsx|xls|pdf|docx|doc)$/i, "");
  };

  const handleResetFilters = () => {
    setSelectedYear(null);
    setSelectedTable(null);
    setSelectedRegion(null);
    setSelectedCategory(null);
    setSelectedDepartment(null);
    setSelectedFacility(null);
    setSelectedCity(null);
    setSelectedVisitType(null);
    if (active) {
      refreshWorkspace(active.id, null, null, null, null, null, null, null, null);
    }
  };

  return (
    <div className={`app-shell theme-${theme}`}>
      <Sidebar
        projects={projects}
        activeProject={active}
        onSelect={setActive}
        onCreate={createProject}
        onDeleteProject={deleteProject}
        activeView={activeView}
        onSelectView={setActiveView}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <main className="main">
        {/* Topbar */}
        <header className="topbar">
          <div>
            <span className="eyebrow">ENTERPRISE INTELLIGENCE WORKSPACE</span>
            <h1>{active?.name || "Welcome to NEXUS AI"}</h1>
          </div>

          <div className="topbar-actions">
            <label className={`upload-button ${busy ? "disabled" : ""}`}>
              <UploadCloud size={16} />
              <span>{busy ? "Processing…" : "Upload Files"}</span>
              <input
                type="file"
                accept=".csv,.xlsx,.pdf,.docx"
                multiple
                onChange={handleFileInput}
                disabled={!active || busy}
                ref={fileInputRef}
              />
            </label>
          </div>
        </header>

        {/* Upload Queue Status */}
        {uploadQueue.length > 0 && (
          <div className="upload-queue">
            <div className="upload-queue-header">
              <span>Upload Progress ({uploadQueue.filter(f => f.status === "success").length}/{uploadQueue.length} complete)</span>
              <button className="btn-close-notice" onClick={() => setUploadQueue([])}>✕</button>
            </div>
            {uploadQueue.map((f, i) => (
              <div key={i} className={`upload-queue-item status-${f.status}`}>
                <span className="uq-name" title={f.name}>{f.name}</span>
                <span className="uq-status">
                  {f.status === "pending" && "Queued"}
                  {f.status === "uploading" && <><Loader2 size={12} className="spin" /> Uploading…</>}
                  {f.status === "success" && <><CheckCircle2 size={12} /> Done</>}
                  {f.status === "error" && (
                    <div className="uq-error-wrap">
                      <span className="uq-error-msg"><AlertCircle size={12} /> {f.error}</span>
                      {(f.error?.includes("50 MB") || f.rawFile?.size > 50 * 1024 * 1024) && f.rawFile && (
                        <button
                          type="button"
                          className="btn-split-retry"
                          onClick={() => setPendingSplitFile(f.rawFile)}
                          title="Split this large file into parts and upload"
                        >
                          <Scissors size={11} /> Split into Parts
                        </button>
                      )}
                    </div>
                  )}
                </span>
              </div>
            ))}
          </div>
        )}

        {/* Global Notifications */}
        {notice && (
          <div className="notice" role="status">
            <span>{notice}</span>
            <button className="btn-close-notice" onClick={() => setNotice("")}>✕</button>
          </div>
        )}

        {/* Empty State when no workspace is active */}
        {!active ? (
          <div
            className={`welcome ${isDragOver ? "drag-over" : ""}`}
            onDrop={(e) => { handleDrop(e); }}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
          >
            <UploadCloud size={48} style={{ color: "#3B82F6", marginBottom: 16 }} />
            <h2>Create Your First Analytics Workspace</h2>
            <p>Ingest structured CSV/Excel files and enterprise PDF/DOCX reports into a unified, local-first analytical environment.</p>
            <button onClick={createProject}>Create Workspace</button>
          </div>
        ) : (
          <>
            {/* Quick Workspace Stats Bar */}
            <section className="metrics">
              <Metric
                icon={<Files />}
                label="Total Files"
                value={dashboard?.dataset_count ?? "0"}
              />
              <Metric
                icon={<Table2 />}
                label="Structured Tables"
                value={dashboard?.structured_dataset_count ?? "0"}
              />
              <Metric
                icon={<BarChart3 />}
                label="Indexed Rows"
                value={dashboard?.total_rows?.toLocaleString() ?? "0"}
              />
              <Metric
                icon={<RefreshCw />}
                label="Document Reports"
                value={dashboard?.document_count ?? "0"}
              />
            </section>

            {/* View Switching */}
            {activeView === "dashboard" && (
              <DashboardView
                dashboard={dashboard}
                activeTable={selectedTable}
                onSelectTable={(tbl) => {
                  setSelectedTable(tbl);
                  refreshWorkspace(active.id, tbl, selectedYear, selectedRegion, selectedCategory, selectedDepartment, selectedFacility, selectedCity, selectedVisitType);
                }}
                selectedYear={selectedYear}
                onSelectYear={(yr) => {
                  setSelectedYear(yr);
                  refreshWorkspace(active.id, selectedTable, yr, selectedRegion, selectedCategory, selectedDepartment, selectedFacility, selectedCity, selectedVisitType);
                }}
                selectedRegion={selectedRegion}
                onSelectRegion={(reg) => {
                  setSelectedRegion(reg);
                  refreshWorkspace(active.id, selectedTable, selectedYear, reg, selectedCategory, selectedDepartment, selectedFacility, selectedCity, selectedVisitType);
                }}
                selectedCategory={selectedCategory}
                onSelectCategory={(cat) => {
                  setSelectedCategory(cat);
                  refreshWorkspace(active.id, selectedTable, selectedYear, selectedRegion, cat, selectedDepartment, selectedFacility, selectedCity, selectedVisitType);
                }}
                selectedDepartment={selectedDepartment}
                onSelectDepartment={(dept) => {
                  setSelectedDepartment(dept);
                  refreshWorkspace(active.id, selectedTable, selectedYear, selectedRegion, selectedCategory, dept, selectedFacility, selectedCity, selectedVisitType);
                }}
                selectedFacility={selectedFacility}
                onSelectFacility={(fac) => {
                  setSelectedFacility(fac);
                  refreshWorkspace(active.id, selectedTable, selectedYear, selectedRegion, selectedCategory, selectedDepartment, fac, selectedCity, selectedVisitType);
                }}
                selectedCity={selectedCity}
                onSelectCity={(city) => {
                  setSelectedCity(city);
                  refreshWorkspace(active.id, selectedTable, selectedYear, selectedRegion, selectedCategory, selectedDepartment, selectedFacility, city, selectedVisitType);
                }}
                selectedVisitType={selectedVisitType}
                onSelectVisitType={(vt) => {
                  setSelectedVisitType(vt);
                  refreshWorkspace(active.id, selectedTable, selectedYear, selectedRegion, selectedCategory, selectedDepartment, selectedFacility, selectedCity, vt);
                }}
                onResetFilters={handleResetFilters}
              />
            )}

            {activeView === "insights" && (
              <InsightsView
                insights={insights}
                onAskFollowUp={(prompt) => {
                  setActiveView("chat");
                  handleAsk(prompt);
                }}
              />
            )}

            {activeView === "reports" && (
              <ReportsView projectId={active?.id} />
            )}

            {activeView === "chat" && (
              <div className={`workspace-grid ${isFilesCollapsed ? "files-panel-collapsed" : ""}`}>
                <ChatPanel
                  onAsk={handleAsk}
                  busy={busy}
                  messages={messages}
                  onNewChat={handleNewChat}
                  mode={chatMode}
                  onModeChange={setChatMode}
                />

                {/* Right Panel: Uploaded Workspace Files */}
                <aside
                  className={`data-panel ${isDragOver ? "drag-over" : ""} ${isFilesCollapsed ? "collapsed-box" : ""}`}
                  onDrop={handleDrop}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                >
                  <div className="section-heading">
                    <div>
                      <span className="eyebrow">PROJECT ASSETS</span>
                      <h2>Uploaded Files ({datasets.length})</h2>
                    </div>
                    <div className="panel-actions-group">
                      <label className="btn-upload-small" title="Upload more files">
                        <UploadCloud size={14} />
                        <input
                          type="file"
                          accept=".csv,.xlsx,.pdf,.docx"
                          multiple
                          onChange={handleFileInput}
                          disabled={busy}
                        />
                      </label>
                      <button
                        className="btn-toggle-minimize"
                        onClick={() => setIsFilesCollapsed(prev => !prev)}
                        title={isFilesCollapsed ? "Expand files list" : "Minimize files list"}
                      >
                        {isFilesCollapsed ? <ChevronDown size={15} /> : <ChevronUp size={15} />}
                      </button>
                    </div>
                  </div>

                  {!isFilesCollapsed && datasets.length > 0 && (
                    <div className="dataset-scope-bar">
                      <span className="scope-indicator">
                        {selectedDatasetIds.length === 0
                          ? `Querying All Files (${datasets.length})`
                          : `Targeting ${selectedDatasetIds.length} of ${datasets.length} Files`}
                      </span>
                      {selectedDatasetIds.length > 0 && (
                        <button
                          className="btn-reset-scope"
                          onClick={selectAllDatasets}
                          title="Reset to all files"
                        >
                          Select All
                        </button>
                      )}
                    </div>
                  )}

                  {!isFilesCollapsed && isDragOver && (
                    <div className="drop-zone-overlay">
                      <UploadCloud size={32} />
                      <span>Drop files to upload</span>
                    </div>
                  )}

                  {!isFilesCollapsed && (
                    <div className="dataset-list">
                      {datasets.length === 0 ? (
                        <div className="empty-data">
                          No files in this workspace yet.<br />
                          Upload a CSV, Excel, PDF, or DOCX document to begin,
                          or drag &amp; drop files here.
                        </div>
                      ) : (
                        datasets.map(d => {
                          const isSelected = selectedDatasetIds.length === 0 || selectedDatasetIds.includes(d.id);
                          const cleanName = getCleanDisplayName(d);
                          return (
                            <div
                              className={`dataset-item ${isSelected ? "is-selected-scope" : "is-excluded-scope"}`}
                              key={d.id}
                            >
                              <label className="dataset-checkbox-wrap" title="Toggle file for AI query scope">
                                <input
                                  type="checkbox"
                                  checked={isSelected}
                                  onChange={() => toggleDatasetSelection(d.id)}
                                />
                              </label>

                              <div className="dataset-item-left">
                                <span className={`file-badge badge-${d.file_type}`}>
                                  {d.file_type.toUpperCase()}
                                </span>
                                <div className="dataset-meta">
                                  <b title={d.original_filename || d.filename}>{cleanName}</b>
                                  <small>
                                    {d.table_name
                                      ? `${d.row_count.toLocaleString()} rows`
                                      : `${d.row_count} chunks indexed`}
                                    {d.created_at && (
                                      <span> · {new Date(d.created_at).toLocaleDateString([], { month: "short", day: "numeric" })}</span>
                                    )}
                                  </small>
                                </div>
                              </div>

                              <div className="dataset-item-actions">
                                {d.table_name && (
                                  <button
                                    className="btn-icon"
                                    title="Preview data"
                                    onClick={() => previewDataset(d.id)}
                                  >
                                    <Eye size={14} />
                                  </button>
                                )}
                                <a
                                  className="btn-icon"
                                  title="Download original file"
                                  href={`/api/projects/${active.id}/datasets/${d.id}/download`}
                                  download
                                >
                                  <Download size={14} />
                                </a>
                                <button
                                  className="btn-icon text-red"
                                  title="Delete file"
                                  onClick={() => deleteDataset(d.id, d.original_filename || d.filename)}
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            </div>
                          );
                        })
                      )}
                    </div>
                  )}

                  {!isFilesCollapsed && (
                    <div className="data-note">
                      Supported: CSV, XLSX, PDF, DOCX (Max 50MB) · Drag &amp; drop enabled
                    </div>
                  )}
                </aside>
              </div>
            )}
          </>
        )}

        {/* Modal for viewing structured dataset rows */}
        <DatasetPreviewModal
          preview={previewData}
          onClose={() => setPreviewData(null)}
        />

        {/* Modal for Chunking and Splitting Large Files (>50MB) */}
        <LargeFileSplitModal
          file={pendingSplitFile}
          onClose={() => setPendingSplitFile(null)}
          onSplitAndUpload={handleSplitAndUploadFile}
          onUploadSingle={handleDirectUploadFile}
        />
      </main>
    </div>
  );
}

function Metric({ icon, label, value }) {
  return (
    <div className="metric-card">
      <div className="metric-icon">{icon}</div>
      <div>
        <small>{label}</small>
        <strong>{value}</strong>
      </div>
    </div>
  );
}
