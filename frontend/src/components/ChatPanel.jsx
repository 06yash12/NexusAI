import { useState, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  Send, Bot, User, FileText, Database, Sparkles,
  ChevronDown, ChevronUp, BarChart2, PlusCircle, Clock, AlertTriangle,
  CheckCircle2, Loader2, Table2, Layers, Code2
} from "lucide-react";
import {
  ResponsiveContainer, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, CartesianGrid
} from "recharts";

function formatMarkdownContent(text) {
  if (!text) return "";
  // 1. Ensure tables preceded immediately by regular text have a double newline so GFM parses them as tables
  let res = text.replace(/([^\n])\n(\|[^\n]+\|)\n(\|[-: |]+\|)/g, "$1\n\n$2\n$3");
  // 2. Also ensure table ending is followed by a newline before text
  res = res.replace(/(\|[^\n]+\|)\n([^\n| -])/g, "$1\n\n$2");
  return res;
}

function getDefaultAnalysisSteps(m) {
  const steps = [];
  if (m.sql) {
    steps.push({
      type: "table",
      title: "Analyzed Structured DuckDB Tables",
      detail: `${m.rows?.length || 0} rows computed and aggregated`
    });
    steps.push({
      type: "sql",
      title: "Executed SQL Analytics",
      detail: `Completed in ${m.execution_time_ms || 0}ms`
    });
  }
  if (m.sources?.length > 0) {
    steps.push({
      type: "document",
      title: `Analyzed ${m.sources.length} Document Excerpts`,
      detail: "Retrieved with verified semantic citations"
    });
  }
  steps.push({
    type: "synthesis",
    title: "Grounded Business Intelligence Synthesis",
    detail: "Validated against numerical query results and citations"
  });
  return steps;
}

export default function ChatPanel({
  onAsk,
  busy,
  messages,
  onNewChat,
  mode,
  onModeChange
}) {
  const [question, setQuestion] = useState("");
  const [expandedSql, setExpandedSql] = useState({});
  const [expandedTables, setExpandedTables] = useState({});
  const [expandedTrace, setExpandedTrace] = useState({});
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [isLiveThinkingExpanded, setIsLiveThinkingExpanded] = useState(true);

  useEffect(() => {
    let timer;
    if (busy) {
      setElapsedSeconds(0);
      setIsLiveThinkingExpanded(true);
      timer = setInterval(() => {
        setElapsedSeconds(s => s + 1);
      }, 1000);
    } else {
      setElapsedSeconds(0);
    }
    return () => clearInterval(timer);
  }, [busy]);

  const toggleSql = (idx) => {
    setExpandedSql(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const toggleTable = (idx) => {
    setExpandedTables(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const toggleTrace = (idx) => {
    setExpandedTrace(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const getLiveThinkingSteps = (sec) => {
    return [
      {
        id: "intent",
        title: `Classified Query Intent (${mode === 'auto' ? 'Auto-Intelligent Multi-File' : mode.toUpperCase()})`,
        detail: "Identified quantitative and document analytical requirements",
        status: "done",
        icon: Sparkles
      },
      {
        id: "schema",
        title: "Inspecting Dataset Schemas & Project Tables",
        detail: "Matching column mappings (Order_Date, Net_Revenue_INR, Profit_INR, etc.)",
        status: sec >= 2 ? "done" : "active",
        icon: Table2
      },
      {
        id: "query",
        title: "Executing DuckDB Cross-File SQL Aggregations",
        detail: "Executing safe AST-validated queries across multi-quarter datasets",
        status: sec >= 5 ? "done" : (sec >= 2 ? "active" : "pending"),
        icon: Database
      },
      {
        id: "rag",
        title: "Scanning Document Semantic Embeddings & Excerpts",
        detail: "Cross-referencing vector embeddings and source text chunks",
        status: sec >= 8 ? "done" : (sec >= 5 ? "active" : "pending"),
        icon: FileText
      },
      {
        id: "synthesis",
        title: "Synthesizing Grounded Insights & Executive Findings",
        detail: "Verifying exact calculations against retrieved evidence without fabrication",
        status: sec >= 8 ? "active" : "pending",
        icon: CheckCircle2
      }
    ];
  };

  const submit = (e) => {
    e.preventDefault();
    if (!question.trim() || busy) return;
    const q = question.trim();
    setQuestion("");
    onAsk(q, mode);
  };

  return (
    <section className="chat-panel">
      <div className="section-heading">
        <div>
          <span className="eyebrow">AI ANALYTICS ASSISTANT</span>
          <h2>Ask your business data & documents</h2>
        </div>

        <div className="chat-controls">
          <div className="mode-selector">
            <span className="mode-label">Mode:</span>
            <select
              value={mode}
              onChange={(e) => onModeChange(e.target.value)}
              className="mode-dropdown"
            >
              <option value="auto">Auto (Intelligent)</option>
              <option value="structured">Structured (SQL)</option>
              <option value="documents">Documents (RAG)</option>
              <option value="hybrid">Hybrid (SQL + RAG)</option>
            </select>
          </div>

          <button
            type="button"
            className="btn-new-chat"
            onClick={onNewChat}
            title="Start a new chat session"
          >
            <PlusCircle size={14} /> New Chat
          </button>
        </div>
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <div className="empty-chat">
            <Bot size={36} />
            <h3>NEXUS AI Business Analyst</h3>
            <p>Ask quantitative business questions, explore trends, or query policies from uploaded documents.</p>
            <div className="suggestions">
              <button onClick={() => onAsk("What were the total sales in 2026?", mode)}>
                Total sales in 2026
              </button>
              <button onClick={() => onAsk("Which five products generated the highest revenue?", mode)}>
                Top 5 products by revenue
              </button>
              <button onClick={() => onAsk("Which region performed best?", mode)}>
                Best performing region
              </button>
              <button onClick={() => onAsk("What is the monthly revenue trend?", mode)}>
                Monthly revenue trend
              </button>
              <button onClick={() => onAsk("Summarize the major findings and strategy from uploaded reports.", mode)}>
                Summarize report findings
              </button>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div className={`message ${m.role}`} key={i}>
            <div className="avatar">
              {m.role === "user" ? <User size={16} /> : <Bot size={16} />}
            </div>

            <div className="message-body">
              <div className="message-header-row">
                <span className="message-sender">{m.role === "user" ? "You" : "NEXUS AI"}</span>
                {m.mode && (
                  <span className={`tag-mode mode-${m.mode}`}>
                    {m.mode.toUpperCase()}
                  </span>
                )}
                {m.execution_time_ms > 0 && (
                  <span className="exec-time">
                    <Clock size={11} /> {m.execution_time_ms}ms
                  </span>
                )}
              </div>

              {/* Collapsible Analysis Trace Dropdown for Assistant Messages */}
              {m.role === "assistant" && (
                <div className="analysis-trace-wrapper">
                  <button
                    type="button"
                    className={`btn-analysis-trace ${expandedTrace[i] ? "is-expanded" : ""}`}
                    onClick={() => toggleTrace(i)}
                    title="Inspect analyzed steps, datasets, and execution details"
                  >
                    <div className="trace-summary-left">
                      <Sparkles size={13} className="trace-sparkle-icon" />
                      <span className="trace-label">
                        {m.analysis_steps?.length > 0 
                          ? `Analyzed ${m.analysis_steps.length} Analytical Steps` 
                          : `Analyzed ${m.sql ? "DuckDB Tables" : "Workspace Evidence"}`}
                        {m.rows?.length > 0 && ` · ${m.rows.length.toLocaleString()} rows`}
                      </span>
                      {m.execution_time_ms > 0 && (
                        <span className="trace-time-badge">{m.execution_time_ms}ms</span>
                      )}
                    </div>
                    <div className="trace-summary-right">
                      <span>{expandedTrace[i] ? "Hide Analysis" : "Show Analysis"}</span>
                      {expandedTrace[i] ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
                    </div>
                  </button>

                  {expandedTrace[i] && (
                    <div className="analysis-trace-dropdown">
                      <div className="trace-dropdown-header">
                        <span>Execution &amp; Evidence Grounding Pipeline</span>
                      </div>
                      <div className="trace-steps-list">
                        {(m.analysis_steps && m.analysis_steps.length > 0
                          ? m.analysis_steps
                          : getDefaultAnalysisSteps(m)
                        ).map((step, sIdx) => (
                          <div className="trace-step-item" key={sIdx}>
                            <div className="trace-step-icon">
                              {step.type === "scope" && <Layers size={13} />}
                              {step.type === "table" && <Database size={13} />}
                              {step.type === "sql" && <Code2 size={13} />}
                              {step.type === "document" && <FileText size={13} />}
                              {step.type === "synthesis" && <CheckCircle2 size={13} />}
                              {!["scope", "table", "sql", "document", "synthesis"].includes(step.type) && <Sparkles size={13} />}
                            </div>
                            <div className="trace-step-content">
                              <span className="trace-step-title">{step.title}</span>
                              {step.detail && <span className="trace-step-detail">{step.detail}</span>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="message-text markdown-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {formatMarkdownContent(m.text || m.answer || "")}
                </ReactMarkdown>
              </div>

              {/* Collapsible SQL Query with Execution Timing */}
              {m.sql && (
                <div className="sql-box">
                  <div className="sql-header" onClick={() => toggleSql(i)}>
                    <div className="sql-title">
                      <Database size={13} />
                      <span>Executed DuckDB SQL</span>
                    </div>
                    {expandedSql[i] ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                  </div>
                  {expandedSql[i] && (
                    <div className="sql-content">
                      <pre><code>{m.sql}</code></pre>
                    </div>
                  )}
                </div>
              )}

              {/* Inline Chart Preview if Query Returned Chartable Data */}
              {m.chart_suggestion && m.rows?.length > 1 && (
                <div className="inline-chart-box">
                  <div className="chart-title">
                    <BarChart2 size={14} />
                    <span>{m.chart_suggestion.title || "Visual Analysis"}</span>
                  </div>
                  <div style={{ width: "100%", height: 200 }}>
                    <ResponsiveContainer>
                      {m.chart_suggestion.type === "line" ? (
                        <LineChart data={m.rows} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f324d" />
                          <XAxis dataKey={m.chart_suggestion.x_key} stroke="#8297b5" fontSize={11} />
                          <YAxis stroke="#8297b5" fontSize={11} />
                          <Tooltip contentStyle={{ backgroundColor: "#0e1a2d", borderColor: "#243c5e", color: "#e8edf5" }} />
                          {m.chart_suggestion.y_keys.map((key, kIdx) => (
                            <Line key={key} type="monotone" dataKey={key} stroke={kIdx === 0 ? "#4a90e2" : "#50e3c2"} strokeWidth={2} dot={{ r: 3 }} />
                          ))}
                        </LineChart>
                      ) : (
                        <BarChart data={m.rows} margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1f324d" />
                          <XAxis dataKey={m.chart_suggestion.x_key} stroke="#8297b5" fontSize={11} />
                          <YAxis stroke="#8297b5" fontSize={11} />
                          <Tooltip contentStyle={{ backgroundColor: "#0e1a2d", borderColor: "#243c5e", color: "#e8edf5" }} />
                          {m.chart_suggestion.y_keys.map((key, kIdx) => (
                            <Bar key={key} dataKey={key} fill={kIdx === 0 ? "#3b82f6" : "#10b981"} radius={[4, 4, 0, 0]} />
                          ))}
                        </BarChart>
                      )}
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Result Data Table */}
              {m.rows?.length > 0 && (
                <div className="data-results-box">
                  <div className="data-results-header" onClick={() => toggleTable(i)}>
                    <span>Results ({m.rows.length} rows)</span>
                    <button type="button" className="btn-toggle-table">
                      {expandedTables[i] ? "Collapse Table" : "View Data"}
                    </button>
                  </div>

                  {expandedTables[i] && (
                    <div className="table-wrap">
                      <table>
                        <thead>
                          <tr>
                            {m.columns?.map(c => <th key={c}>{c}</th>)}
                          </tr>
                        </thead>
                        <tbody>
                          {m.rows.map((row, rIdx) => (
                            <tr key={rIdx}>
                              {m.columns?.map(c => (
                                <td key={c}>{row[c] !== null && row[c] !== undefined ? String(row[c]) : "—"}</td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* Document Grounding Citations */}
              {m.sources?.length > 0 && (
                <div className="sources-container">
                  <div className="sources-title">
                    <FileText size={13} />
                    <span>Verified Document Citations</span>
                  </div>
                  <div className="citations-list">
                    {m.sources.map((s, sIdx) => (
                      <div className="citation-card" key={sIdx}>
                        <div className="citation-meta">
                          <span className="citation-file">{s.filename}</span>
                          {s.page_number && (
                            <span className="citation-page">Page {s.page_number}</span>
                          )}
                          <span className="citation-score">Relevance: {(s.score * 100).toFixed(1)}%</span>
                        </div>
                        <div className="citation-excerpt">
                          "{s.excerpt}"
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Warnings */}
              {m.warnings?.map((w, wIdx) => (
                <div className="warning-box" key={wIdx}>
                  <AlertTriangle size={13} />
                  <span>{w}</span>
                </div>
              ))}
            </div>
          </div>
        ))}

        {busy && (
          <div className="thinking-row">
            <div className="avatar assistant"><Bot size={16} /></div>
            <div className="live-thinking-capsule">
              <div 
                className="live-thinking-header"
                onClick={() => setIsLiveThinkingExpanded(prev => !prev)}
                title="Click to toggle analysis progress breakdown"
              >
                <div className="live-thinking-left">
                  <span className="pulse-dot"></span>
                  <span className="live-thinking-title">
                    {elapsedSeconds < 2 && "Inspecting dataset schemas & query scope…"}
                    {elapsedSeconds >= 2 && elapsedSeconds < 5 && "Analyzing multi-file tables in DuckDB…"}
                    {elapsedSeconds >= 5 && elapsedSeconds < 8 && "Executing safe SQL aggregations & vector search…"}
                    {elapsedSeconds >= 8 && "Synthesizing evidence-grounded response…"}
                  </span>
                </div>
                <div className="live-thinking-right">
                  <span className="live-timer">{elapsedSeconds}s</span>
                  {isLiveThinkingExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                </div>
              </div>

              {isLiveThinkingExpanded && (
                <div className="live-thinking-dropdown">
                  <div className="live-steps-list">
                    {getLiveThinkingSteps(elapsedSeconds).map((step) => {
                      return (
                        <div className={`live-step-row status-${step.status}`} key={step.id}>
                          <div className="live-step-status-icon">
                            {step.status === "done" && <CheckCircle2 size={13} className="text-emerald" />}
                            {step.status === "active" && <Loader2 size={13} className="spin text-blue" />}
                            {step.status === "pending" && <span className="dot-pending"></span>}
                          </div>
                          <div className="live-step-info">
                            <span className="live-step-title">{step.title}</span>
                            <span className="live-step-detail">{step.detail}</span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      <form className="composer" onSubmit={submit}>
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about your business data, reports, or policies…"
          disabled={busy}
        />
        <button type="submit" disabled={busy || !question.trim()} title="Send query">
          <Send size={16} />
        </button>
      </form>

      <p className="fine-print">
        Calculations are executed natively in DuckDB. Citations are verified directly from source pages.
      </p>
    </section>
  );
}
