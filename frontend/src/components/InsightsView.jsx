import { 
  TrendingUp, AlertCircle, Sparkles, Lightbulb,
  CheckCircle2, ArrowRight, ShieldAlert 
} from "lucide-react";

export default function InsightsView({ insights, onAskFollowUp }) {
  if (!insights) {
    return <div className="loading-state">Synthesizing business insights from workspace data…</div>;
  }

  const items = insights.insights || [];
  const recs = insights.recommendations || [];

  const getImportanceBadge = (imp) => {
    switch (imp) {
      case "high":
        return <span className="badge-importance badge-high">High Impact</span>;
      case "medium":
        return <span className="badge-importance badge-medium">Medium</span>;
      default:
        return <span className="badge-importance badge-low">Low</span>;
    }
  };

  const getInsightIcon = (type) => {
    switch (type) {
      case "trend":
        return <TrendingUp size={18} className="text-blue" />;
      case "anomaly":
        return <AlertCircle size={18} className="text-yellow" />;
      case "underperformance":
        return <ShieldAlert size={18} className="text-red" />;
      default:
        return <Sparkles size={18} className="text-emerald" />;
    }
  };

  return (
    <div className="insights-view">
      <div className="section-heading">
        <div>
          <span className="eyebrow">AUTOMATED BUSINESS INTELLIGENCE</span>
          <h2>Analytical Findings & Strategic Recommendations</h2>
        </div>
        <span className="local-pill">● Grounded in Real Data</span>
      </div>

      {insights.summary && (
        <div className="insights-summary-box">
          <Lightbulb size={20} className="text-yellow" />
          <div>
            <b>Synthesis Summary</b>
            <p>{insights.summary}</p>
          </div>
        </div>
      )}

      <div className="insights-grid">
        {/* Left Column: Data-Backed Observations */}
        <div className="findings-col">
          <div className="col-header">
            <h3>Verified Analytical Observations</h3>
            <span className="count-badge">{items.length}</span>
          </div>

          {items.length === 0 ? (
            <div className="empty-insights">
              Upload multi-period structured datasets to generate trend, anomaly, and regional variance observations.
            </div>
          ) : (
            items.map((item, idx) => (
              <div className="insight-card" key={idx}>
                <div className="insight-card-top">
                  <div className="insight-icon-row">
                    {getInsightIcon(item.type)}
                    <b>{item.title}</b>
                  </div>
                  {getImportanceBadge(item.importance)}
                </div>
                <p className="insight-desc">{item.description}</p>
                <div className="insight-metric-pill">
                  <span>Metric: </span>
                  <strong>{item.supporting_metric}</strong>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Right Column: Evidence-Grounded Recommendations */}
        <div className="recommendations-col">
          <div className="col-header">
            <h3>Strategic Recommendations</h3>
            <span className="count-badge">{recs.length}</span>
          </div>

          {recs.length === 0 ? (
            <div className="empty-insights">
              Recommendations will appear when actionable disparities or trends are detected in the dataset.
            </div>
          ) : (
            recs.map((rec, idx) => (
              <div className="rec-card" key={idx}>
                <div className="rec-card-header">
                  <CheckCircle2 size={16} className="text-emerald" />
                  <h4>{rec.recommendation}</h4>
                </div>
                <div className="rec-section">
                  <span className="rec-label">Rationale:</span>
                  <p>{rec.rationale}</p>
                </div>
                <div className="rec-section">
                  <span className="rec-label">Expected Impact:</span>
                  <p>{rec.expected_impact}</p>
                </div>
                <div className="rec-data-evidence">
                  <span className="rec-label">Supporting Evidence:</span>
                  <code>{rec.supporting_data}</code>
                </div>
                {onAskFollowUp && (
                  <button 
                    className="btn-ask-rec"
                    onClick={() => onAskFollowUp(`Explain how to implement this recommendation: "${rec.recommendation}" based on our business data`)}
                  >
                    <span>Analyze in Chat</span>
                    <ArrowRight size={13} />
                  </button>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
