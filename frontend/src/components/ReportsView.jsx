import { useState } from "react";
import {
  FileBarChart, FileSpreadsheet, FileText, Download,
  Loader2, CheckCircle2, AlertCircle, ChevronRight
} from "lucide-react";

const REPORT_TYPES = [
  {
    id: "full",
    icon: <FileBarChart size={22} />,
    label: "Full Business Intelligence Report",
    desc: "Complete report: KPIs, monthly trend, regional, category, top products, YoY comparison, strategic recommendations.",
    color: "#3B82F6"
  },
  {
    id: "sales",
    icon: <FileBarChart size={22} />,
    label: "Sales Performance Report",
    desc: "Revenue, orders, units sold, monthly trend and geographic breakdown.",
    color: "#10B981"
  },
  {
    id: "product",
    icon: <FileBarChart size={22} />,
    label: "Product Performance Report",
    desc: "Top products ranked by revenue and profit, category-wise analysis.",
    color: "#8B5CF6"
  },
];

export default function ReportsView({ projectId }) {
  const [generating, setGenerating] = useState(null); // "excel" | "pdf" | null
  const [lastResult, setLastResult] = useState(null); // { type, success, error }
  const [selectedType, setSelectedType] = useState("full");

  async function handleDownload(format) {
    if (!projectId) return;
    setGenerating(format);
    setLastResult(null);

    try {
      const url = `/api/projects/${projectId}/reports/${format}?report_type=${selectedType}`;
      const res = await fetch(url);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || "Report generation failed");
      }

      // Trigger browser download
      const blob = await res.blob();
      const ext = format === "excel" ? "xlsx" : "pdf";
      const contentDisp = res.headers.get("Content-Disposition") || "";
      const match = contentDisp.match(/filename="([^"]+)"/);
      const filename = match ? match[1] : `nexus_report.${ext}`;

      const blobUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(blobUrl);

      setLastResult({ type: format, success: true, filename });
    } catch (err) {
      setLastResult({ type: format, success: false, error: err.message });
    } finally {
      setGenerating(null);
    }
  }

  return (
    <div className="reports-view">
      <div className="section-heading">
        <div>
          <span className="eyebrow">BUSINESS REPORTING</span>
          <h2>Reports &amp; Data Export</h2>
        </div>
        <p className="reports-subtitle">
          Generate comprehensive business intelligence reports from your uploaded datasets.
          All calculations use real data from your DuckDB workspace — no fabricated results.
        </p>
      </div>

      {!projectId && (
        <div className="report-notice">
          <AlertCircle size={18} />
          <span>Select a workspace to generate reports.</span>
        </div>
      )}

      {/* Report Type Selection */}
      <div className="report-type-grid">
        {REPORT_TYPES.map(rt => (
          <div
            key={rt.id}
            className={`report-type-card ${selectedType === rt.id ? "selected" : ""}`}
            onClick={() => setSelectedType(rt.id)}
            style={{ "--accent": rt.color }}
          >
            <div className="report-type-icon" style={{ color: rt.color }}>{rt.icon}</div>
            <div className="report-type-info">
              <strong>{rt.label}</strong>
              <span>{rt.desc}</span>
            </div>
            {selectedType === rt.id && (
              <ChevronRight size={16} className="report-selected-check" style={{ color: rt.color }} />
            )}
          </div>
        ))}
      </div>

      {/* Download Buttons */}
      <div className="report-downloads">
        <div className="report-download-card">
          <div className="report-dl-icon">
            <FileSpreadsheet size={28} style={{ color: "#10B981" }} />
          </div>
          <div className="report-dl-info">
            <strong>Excel Workbook (.xlsx)</strong>
            <span>Multi-sheet workbook with KPIs, monthly trend, regional, category, top products, YoY comparison and recommendations.</span>
          </div>
          <button
            className={`btn-report-dl excel ${generating === "excel" ? "loading" : ""}`}
            onClick={() => handleDownload("excel")}
            disabled={!projectId || generating !== null}
          >
            {generating === "excel"
              ? <><Loader2 size={16} className="spin" /> Generating…</>
              : <><Download size={16} /> Download Excel</>
            }
          </button>
        </div>

        <div className="report-download-card">
          <div className="report-dl-icon">
            <FileText size={28} style={{ color: "#EF4444" }} />
          </div>
          <div className="report-dl-info">
            <strong>PDF Report (.pdf)</strong>
            <span>Styled business report with executive summary, charts tables, strategic findings and actionable recommendations.</span>
          </div>
          <button
            className={`btn-report-dl pdf ${generating === "pdf" ? "loading" : ""}`}
            onClick={() => handleDownload("pdf")}
            disabled={!projectId || generating !== null}
          >
            {generating === "pdf"
              ? <><Loader2 size={16} className="spin" /> Generating…</>
              : <><Download size={16} /> Download PDF</>
            }
          </button>
        </div>
      </div>

      {/* Result Banner */}
      {lastResult && (
        <div className={`report-result ${lastResult.success ? "success" : "error"}`}>
          {lastResult.success
            ? <><CheckCircle2 size={16} /> Report <b>{lastResult.filename}</b> downloaded successfully.</>
            : <><AlertCircle size={16} /> Report generation failed: {lastResult.error}</>
          }
        </div>
      )}

      {/* What's Included */}
      <div className="report-info-box">
        <h3>What's Included</h3>
        <ul>
          <li>✅ <b>Executive KPI Summary</b> — Revenue, Profit, Margin, Orders, Units, AOV, Return Rate</li>
          <li>✅ <b>Monthly Revenue Trend</b> — Month-over-month performance with profit tracking</li>
          <li>✅ <b>Geographic Breakdown</b> — Revenue and profit by region</li>
          <li>✅ <b>Category Analysis</b> — Revenue, profit and margin by product category</li>
          <li>✅ <b>Top Products</b> — Ranked by revenue with margin details</li>
          <li>✅ <b>Year-over-Year Comparison</b> — 2025 vs 2026 side-by-side (when available)</li>
          <li>✅ <b>Strategic Recommendations</b> — AI-generated, grounded in actual data</li>
        </ul>
        <p className="report-accuracy-note">
          All data sourced directly from DuckDB. Cancelled orders excluded from revenue KPIs.
          Returned orders tracked separately. No fabricated or estimated values.
        </p>
      </div>
    </div>
  );
}
