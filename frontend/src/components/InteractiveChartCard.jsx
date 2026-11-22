import { useState } from "react";
import { 
  ResponsiveContainer, BarChart, Bar, LineChart, Line, AreaChart, Area,
  PieChart, Pie, Cell, XAxis, YAxis, Tooltip, CartesianGrid, Legend 
} from "recharts";
import { 
  Maximize2, Settings2, Check, Sparkles 
} from "lucide-react";

const COLORS = [
  "#3b82f6", "#10b981", "#8b5cf6", "#f59e0b", "#ec4899", 
  "#06b6d4", "#6366f1", "#14b8a6", "#f97316", "#84cc16"
];

export default function InteractiveChartCard({
  id,
  title: initialTitle,
  subtitle,
  data = [],
  availableMetrics = ["revenue", "profit", "orders", "units"],
  defaultMetric = "revenue",
  availableDimensions = ["label"],
  defaultDimension = "label",
  sym = "$",
  formatMoney,
  onOpenModal,
  isModal = false
}) {
  // Chart customization state
  const [chartType, setChartType] = useState("bar"); // bar, horizontalBar, line, area, pie, donut, stackedBar
  const [metric, setMetric] = useState(defaultMetric);
  const [dimension, setDimension] = useState(defaultDimension);
  const [sortOrder, setSortOrder] = useState("desc"); // desc, asc, none
  const [topN, setTopN] = useState("all"); // 5, 10, all
  const [showSettings, setShowSettings] = useState(false);
  const [customTitle, setCustomTitle] = useState(initialTitle);
  const [isEditingTitle, setIsEditingTitle] = useState(false);

  // Available chart types based on data suitability
  const getSuggestedType = () => {
    if (dimension.toLowerCase().includes("date") || dimension.toLowerCase().includes("month") || dimension.toLowerCase().includes("year")) {
      return "line";
    }
    return "bar";
  };

  // Format display labels
  const formatValue = (val) => {
    if (val === undefined || val === null) return "0";
    const mLow = String(metric).toLowerCase();
    const isCurrency = mLow.includes("revenue") || mLow.includes("profit") || mLow.includes("billed") || mLow.includes("paid") || mLow.includes("outstanding") || mLow.includes("amount") || mLow.includes("inr");
    if (isCurrency) {
      return formatMoney ? formatMoney(val) : `${sym}${Number(val).toLocaleString()}`;
    }
    return Number(val).toLocaleString();
  };

  // Process data for rendering (filtering Top N, sorting)
  let processedData = [...(data || [])];

  if (sortOrder === "desc") {
    processedData.sort((a, b) => (Number(b[metric]) || 0) - (Number(a[metric]) || 0));
  } else if (sortOrder === "asc") {
    processedData.sort((a, b) => (Number(a[metric]) || 0) - (Number(b[metric]) || 0));
  }

  if (topN !== "all") {
    processedData = processedData.slice(0, Number(topN));
  }

  // Render specific chart based on chartType
  const renderChart = (height = isModal ? 520 : 270) => {
    if (!processedData || processedData.length === 0) {
      return (
        <div className="empty-chart">
          <p>No data available for the selected dimensions.</p>
        </div>
      );
    }

    const tooltipStyle = {
      backgroundColor: "var(--bg-card)",
      borderColor: "var(--border-color)",
      borderRadius: "8px",
      color: "var(--text-main)",
      boxShadow: "0 8px 24px rgba(0,0,0,0.12)"
    };

    switch (chartType) {
      case "line":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <LineChart data={processedData} margin={{ top: 15, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.6} />
              <XAxis dataKey={dimension} stroke="var(--text-muted)" fontSize={11} />
              <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={formatValue} />
              <Tooltip 
                contentStyle={tooltipStyle} 
                formatter={(val) => [formatValue(val), metric.toUpperCase()]} 
              />
              <Legend verticalAlign="top" height={36} />
              <Line 
                type="monotone" 
                dataKey={metric} 
                name={metric.toUpperCase()} 
                stroke="#3b82f6" 
                strokeWidth={2.5} 
                dot={{ r: 3 }} 
                activeDot={{ r: 6 }} 
              />
            </LineChart>
          </ResponsiveContainer>
        );

      case "area":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <AreaChart data={processedData} margin={{ top: 15, right: 20, left: 0, bottom: 20 }}>
              <defs>
                <linearGradient id={`grad-${id}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8}/>
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.05}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.6} />
              <XAxis dataKey={dimension} stroke="var(--text-muted)" fontSize={11} />
              <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={formatValue} />
              <Tooltip 
                contentStyle={tooltipStyle} 
                formatter={(val) => [formatValue(val), metric.toUpperCase()]} 
              />
              <Legend verticalAlign="top" height={36} />
              <Area 
                type="monotone" 
                dataKey={metric} 
                name={metric.toUpperCase()} 
                stroke="#3b82f6" 
                fillOpacity={1} 
                fill={`url(#grad-${id})`} 
              />
            </AreaChart>
          </ResponsiveContainer>
        );

      case "horizontalBar":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart layout="vertical" data={processedData} margin={{ top: 15, right: 30, left: 40, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.6} />
              <XAxis type="number" stroke="var(--text-muted)" fontSize={11} tickFormatter={formatValue} />
              <YAxis type="category" dataKey={dimension} stroke="var(--text-muted)" fontSize={11} width={80} />
              <Tooltip 
                contentStyle={tooltipStyle} 
                formatter={(val) => [formatValue(val), metric.toUpperCase()]} 
              />
              <Legend verticalAlign="top" height={36} />
              <Bar dataKey={metric} name={metric.toUpperCase()} fill="#3b82f6" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        );

      case "pie":
      case "donut":
        const isDonut = chartType === "donut";
        return (
          <ResponsiveContainer width="100%" height={height}>
            <PieChart margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
              <Tooltip 
                contentStyle={tooltipStyle} 
                formatter={(val) => [formatValue(val), metric.toUpperCase()]} 
              />
              <Legend verticalAlign="bottom" height={36} />
              <Pie
                data={processedData}
                dataKey={metric}
                nameKey={dimension}
                cx="50%"
                cy="50%"
                innerRadius={isDonut ? "55%" : 0}
                outerRadius="80%"
                paddingAngle={isDonut ? 3 : 1}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                labelLine={false}
              >
                {processedData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          </ResponsiveContainer>
        );

      case "stackedBar":
        return (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={processedData} margin={{ top: 15, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.6} />
              <XAxis dataKey={dimension} stroke="var(--text-muted)" fontSize={11} />
              <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={formatValue} />
              <Tooltip contentStyle={tooltipStyle} />
              <Legend verticalAlign="top" height={36} />
              <Bar dataKey="revenue" name="Revenue" stackId="a" fill="#3b82f6" radius={[0, 0, 0, 0]} />
              <Bar dataKey="profit" name="Profit" stackId="a" fill="#10b981" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        );

      case "bar":
      default:
        return (
          <ResponsiveContainer width="100%" height={height}>
            <BarChart data={processedData} margin={{ top: 15, right: 20, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.6} />
              <XAxis dataKey={dimension} stroke="var(--text-muted)" fontSize={11} />
              <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={formatValue} />
              <Tooltip 
                contentStyle={tooltipStyle} 
                formatter={(val) => [formatValue(val), metric.toUpperCase()]} 
              />
              <Legend verticalAlign="top" height={36} />
              <Bar dataKey={metric} name={metric.toUpperCase()} fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        );
    }
  };

  return (
    <div className={`chart-card ${isModal ? "chart-card-modal" : ""}`}>
      {/* Chart Header with Controls */}
      <div className="chart-header">
        <div>
          {subtitle && <span className="eyebrow">{subtitle}</span>}
          {isEditingTitle ? (
            <div className="title-edit-row">
              <input 
                type="text" 
                value={customTitle} 
                onChange={(e) => setCustomTitle(e.target.value)} 
                className="chart-title-input"
                autoFocus
              />
              <button className="btn-icon-subtle" onClick={() => setIsEditingTitle(false)}>
                <Check size={14} />
              </button>
            </div>
          ) : (
            <h3 
              className="editable-chart-title" 
              onClick={() => setIsEditingTitle(true)}
              title="Click to rename chart"
            >
              {customTitle}
            </h3>
          )}
        </div>

        <div className="chart-header-actions">
          {/* Quick AI suggestion button */}
          <button 
            className="btn-chart-action" 
            title="Auto-suggest optimal chart type"
            onClick={() => setChartType(getSuggestedType())}
          >
            <Sparkles size={14} />
          </button>

          {/* Customization Toggle */}
          <button 
            className={`btn-chart-action ${showSettings ? "active" : ""}`}
            title="Customize Chart Metrics & Views"
            onClick={() => setShowSettings(!showSettings)}
          >
            <Settings2 size={14} />
          </button>

          {/* Full-Screen / Maximize */}
          {!isModal && onOpenModal && (
            <button 
              className="btn-chart-action" 
              title="Maximize / Full Screen"
              onClick={() => onOpenModal({
                id,
                title: customTitle,
                subtitle,
                data,
                availableMetrics,
                defaultMetric: metric,
                availableDimensions,
                defaultDimension: dimension,
                sym,
                formatMoney
              })}
            >
              <Maximize2 size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Chart Customization Settings Drawer */}
      {showSettings && (
        <div className="chart-settings-drawer">
          <div className="settings-grid">
            <div className="setting-item">
              <label>Chart Type</label>
              <select value={chartType} onChange={(e) => setChartType(e.target.value)}>
                <option value="bar">Vertical Bar</option>
                <option value="horizontalBar">Horizontal Bar</option>
                <option value="line">Line Chart</option>
                <option value="area">Area Chart</option>
                <option value="pie">Pie Chart</option>
                <option value="donut">Donut Chart</option>
                <option value="stackedBar">Stacked Revenue & Profit</option>
              </select>
            </div>

            <div className="setting-item">
              <label>Metric</label>
              <select value={metric} onChange={(e) => setMetric(e.target.value)}>
                {availableMetrics.map(m => (
                  <option key={m} value={m}>{m.toUpperCase()}</option>
                ))}
              </select>
            </div>

            <div className="setting-item">
              <label>Sort Order</label>
              <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value)}>
                <option value="desc">High to Low (Desc)</option>
                <option value="asc">Low to High (Asc)</option>
                <option value="none">Original Order</option>
              </select>
            </div>

            <div className="setting-item">
              <label>Top N Filter</label>
              <select value={topN} onChange={(e) => setTopN(e.target.value)}>
                <option value="all">All Values</option>
                <option value="5">Top 5 Only</option>
                <option value="10">Top 10 Only</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Render Chart Body */}
      <div className="chart-body">
        {renderChart()}
      </div>
    </div>
  );
}
