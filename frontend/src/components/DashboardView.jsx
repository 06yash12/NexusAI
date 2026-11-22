import { useState } from "react";
import { 
  DollarSign, ShoppingCart, Package, TrendingUp, 
  MapPin, Tag, Award, Database, Calendar, Filter, 
  AlertCircle, CheckCircle2, Maximize2,
  RotateCcw, Bookmark, Check,
  Activity, Users, Clock, Building, Stethoscope, FlaskConical
} from "lucide-react";
import { 
  ResponsiveContainer, BarChart, Bar, LineChart, Line, 
  XAxis, YAxis, Tooltip, CartesianGrid, Legend 
} from "recharts";
import InteractiveChartCard from "./InteractiveChartCard";
import ChartModal from "./ChartModal";

export default function DashboardView({ 
  dashboard, 
  onSelectTable, 
  activeTable,
  selectedYear,
  onSelectYear,
  selectedRegion,
  onSelectRegion,
  selectedCategory,
  onSelectCategory,
  selectedDepartment,
  onSelectDepartment,
  selectedFacility,
  onSelectFacility,
  selectedCity,
  onSelectCity,
  selectedVisitType,
  onSelectVisitType,
  onResetFilters
}) {
  const [trendViewMode, setTrendViewMode] = useState("timeline"); // "timeline" or "yoy"
  const [activeModalChart, setActiveModalChart] = useState(null);
  const [savedViews, setSavedViews] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("nexus_saved_views") || "[]");
    } catch {
      return [];
    }
  });
  const [viewSavedToast, setViewSavedToast] = useState("");

  if (!dashboard) {
    return <div className="loading-state">Loading workspace dashboard…</div>;
  }

  const isHealthcare = dashboard.domain === "healthcare";
  const kpis = dashboard.kpis || [];
  const charts = dashboard.charts || [];
  const monthly = dashboard.monthly_sales || [];
  const yearlyComp = dashboard.yearly_comparison || [];
  const regional = dashboard.regional_sales || [];
  const categories = dashboard.category_sales || [];
  const products = dashboard.top_products || [];
  const tables = Object.keys(dashboard.tables || {});
  const availableYears = dashboard.available_years || [];
  const dims = dashboard.available_dimensions || {};
  const availableRegions = dims.regions || [];
  const availableCategories = dims.categories || [];
  const availableDepartments = dims.departments || [];
  const availableFacilities = dims.facilities || [];
  const availableCities = dims.cities || [];
  const availableVisitTypes = dims.visit_types || [];
  const sym = dashboard.currency_symbol || "$";
  const unavail = dashboard.unavailable_explanations || {};

  const getKpiIcon = (id) => {
    switch (id) {
      case "revenue":
      case "billed_revenue":
        return <DollarSign size={20} />;
      case "collections":
        return <CheckCircle2 size={20} />;
      case "outstanding":
        return <AlertCircle size={20} />;
      case "encounters":
        return <Activity size={20} />;
      case "patients":
        return <Users size={20} />;
      case "avg_wait":
        return <Clock size={20} />;
      case "avg_los":
        return <Calendar size={20} />;
      case "lab_tests":
        return <FlaskConical size={20} />;
      case "orders":
        return <ShoppingCart size={20} />;
      case "quantity":
        return <Package size={20} />;
      case "profit":
        return <Award size={20} />;
      case "aov":
        return <TrendingUp size={20} />;
      default:
        return <Database size={20} />;
    }
  };

  const formatMoney = (val) => {
    if (val === undefined || val === null) return "—";
    const num = Number(val);
    if (Math.abs(num) >= 10000000 && sym === "₹") {
      return `${sym}${(num / 10000000).toFixed(2)} Cr`;
    }
    if (Math.abs(num) >= 100000 && sym === "₹") {
      return `${sym}${(num / 100000).toFixed(2)} L`;
    }
    if (Math.abs(num) >= 1000000) {
      return `${sym}${(num / 1000000).toFixed(2)}M`;
    }
    if (Math.abs(num) >= 1000) {
      return `${sym}${(num / 1000).toFixed(1)}k`;
    }
    return `${sym}${num.toLocaleString()}`;
  };

  // Save current dashboard filter configuration
  const handleSaveView = () => {
    const defaultName = isHealthcare 
      ? (selectedDepartment || selectedFacility || "Custom View")
      : (selectedRegion || selectedCategory || "Custom View");
    const viewName = window.prompt("Name this dashboard view:", defaultName);
    if (!viewName?.trim()) return;

    const newView = {
      id: Date.now(),
      name: viewName.trim(),
      year: selectedYear,
      table: activeTable,
      region: selectedRegion,
      category: selectedCategory,
      department: selectedDepartment,
      facility: selectedFacility,
      city: selectedCity,
      visitType: selectedVisitType
    };

    const updated = [newView, ...savedViews.slice(0, 9)];
    setSavedViews(updated);
    try {
      localStorage.setItem("nexus_saved_views", JSON.stringify(updated));
    } catch {}

    setViewSavedToast(`Saved view "${newView.name}"`);
    setTimeout(() => setViewSavedToast(""), 3500);
  };

  const handleApplySavedView = (view) => {
    if (onSelectYear) onSelectYear(view.year);
    if (onSelectTable) onSelectTable(view.table);
    if (onSelectRegion) onSelectRegion(view.region);
    if (onSelectCategory) onSelectCategory(view.category);
    if (onSelectDepartment) onSelectDepartment(view.department);
    if (onSelectFacility) onSelectFacility(view.facility);
    if (onSelectCity) onSelectCity(view.city);
    if (onSelectVisitType) onSelectVisitType(view.visitType);
  };

  const hasActiveFilters = Boolean(
    selectedYear !== null || 
    activeTable || 
    selectedRegion || 
    selectedCategory ||
    selectedDepartment ||
    selectedFacility ||
    selectedCity ||
    selectedVisitType
  );

  return (
    <div className="dashboard-view">
      {/* Dashboard Topbar & Dynamic Filters Bar */}
      <div className="dashboard-header">
        <div>
          <span className="eyebrow">{dashboard.domain_label ? dashboard.domain_label.toUpperCase() : "EXECUTIVE INTELLIGENCE"}</span>
          <h2>{isHealthcare ? "Healthcare Clinical & Financial Intelligence" : "Business Intelligence Dashboard"}</h2>
          <div className="freshness-row">
            <span className="freshness-tag">{dashboard.data_freshness}</span>
            {dashboard.column_mapping?.billed_revenue && (
              <span className="column-mapped-tag">
                Billed: <code>{dashboard.column_mapping.billed_revenue}</code>
              </span>
            )}
            {dashboard.column_mapping?.paid_amount && (
              <span className="column-mapped-tag">
                Collections: <code>{dashboard.column_mapping.paid_amount}</code>
              </span>
            )}
            {dashboard.column_mapping?.revenue && (
              <span className="column-mapped-tag">
                Revenue: <code>{dashboard.column_mapping.revenue}</code>
              </span>
            )}
            {dashboard.column_mapping?.profit && (
              <span className="column-mapped-tag">
                Profit: <code>{dashboard.column_mapping.profit}</code>
              </span>
            )}
            {viewSavedToast && (
              <span className="view-saved-tag">
                <Check size={12} /> {viewSavedToast}
              </span>
            )}
          </div>
        </div>

        <div className="filter-controls-group">
          {/* Year Filter Buttons */}
          {availableYears.length > 0 && (
            <div className="year-filter-pills">
              <button 
                type="button"
                className={`pill-btn ${selectedYear === null ? "active" : ""}`}
                onClick={() => onSelectYear(null)}
              >
                All Time
              </button>
              {availableYears.map(yr => (
                <button
                  key={yr}
                  type="button"
                  className={`pill-btn ${selectedYear === yr ? "active" : ""}`}
                  onClick={() => onSelectYear(yr)}
                >
                  {yr}
                </button>
              ))}
            </div>
          )}

          {/* Healthcare Filters */}
          {isHealthcare ? (
            <>
              {availableDepartments.length > 0 && (
                <div className="table-filter-wrap">
                  <Stethoscope size={13} />
                  <select 
                    value={selectedDepartment || ""} 
                    onChange={(e) => onSelectDepartment && onSelectDepartment(e.target.value || null)}
                    className="table-filter-select"
                  >
                    <option value="">All Departments</option>
                    {availableDepartments.map(dept => (
                      <option key={dept} value={dept}>{dept}</option>
                    ))}
                  </select>
                </div>
              )}

              {availableFacilities.length > 0 && (
                <div className="table-filter-wrap">
                  <Building size={13} />
                  <select 
                    value={selectedFacility || ""} 
                    onChange={(e) => onSelectFacility && onSelectFacility(e.target.value || null)}
                    className="table-filter-select"
                  >
                    <option value="">All Facilities</option>
                    {availableFacilities.map(fac => (
                      <option key={fac} value={fac}>{fac}</option>
                    ))}
                  </select>
                </div>
              )}

              {availableCities.length > 0 && (
                <div className="table-filter-wrap">
                  <MapPin size={13} />
                  <select 
                    value={selectedCity || ""} 
                    onChange={(e) => onSelectCity && onSelectCity(e.target.value || null)}
                    className="table-filter-select"
                  >
                    <option value="">All Cities</option>
                    {availableCities.map(city => (
                      <option key={city} value={city}>{city}</option>
                    ))}
                  </select>
                </div>
              )}

              {availableVisitTypes.length > 0 && (
                <div className="table-filter-wrap">
                  <Activity size={13} />
                  <select 
                    value={selectedVisitType || ""} 
                    onChange={(e) => onSelectVisitType && onSelectVisitType(e.target.value || null)}
                    className="table-filter-select"
                  >
                    <option value="">All Visit Types</option>
                    {availableVisitTypes.map(vt => (
                      <option key={vt} value={vt}>{vt}</option>
                    ))}
                  </select>
                </div>
              )}
            </>
          ) : (
            <>
              {/* Retail / Sales Filters */}
              {availableRegions.length > 0 && (
                <div className="table-filter-wrap">
                  <MapPin size={13} />
                  <select 
                    value={selectedRegion || ""} 
                    onChange={(e) => onSelectRegion(e.target.value || null)}
                    className="table-filter-select"
                  >
                    <option value="">All Regions</option>
                    {availableRegions.map(reg => (
                      <option key={reg} value={reg}>{reg}</option>
                    ))}
                  </select>
                </div>
              )}

              {availableCategories.length > 0 && (
                <div className="table-filter-wrap">
                  <Tag size={13} />
                  <select 
                    value={selectedCategory || ""} 
                    onChange={(e) => onSelectCategory(e.target.value || null)}
                    className="table-filter-select"
                  >
                    <option value="">All Categories</option>
                    {availableCategories.map(cat => (
                      <option key={cat} value={cat}>{cat}</option>
                    ))}
                  </select>
                </div>
              )}
            </>
          )}

          {/* Table Filter */}
          {tables.length > 1 && (
            <div className="table-filter-wrap">
              <Filter size={13} />
              <select 
                value={activeTable || ""} 
                onChange={(e) => onSelectTable(e.target.value || null)}
                className="table-filter-select"
              >
                <option value="">All Tables</option>
                {tables.map(tbl => (
                  <option key={tbl} value={tbl}>{tbl}</option>
                ))}
              </select>
            </div>
          )}

          {/* Reset Filters button */}
          {hasActiveFilters && (
            <button 
              className="btn-filter-reset" 
              onClick={onResetFilters} 
              title="Reset all filters"
            >
              <RotateCcw size={13} />
              <span>Reset</span>
            </button>
          )}

          {/* Save View Button */}
          <button 
            className="btn-save-view" 
            onClick={handleSaveView}
            title="Save current dashboard view"
          >
            <Bookmark size={13} />
            <span>Save View</span>
          </button>
        </div>
      </div>

      {/* Saved Views Quick Access Bar */}
      {savedViews.length > 0 && (
        <div className="saved-views-bar">
          <span className="saved-views-label">Saved Views:</span>
          <div className="saved-views-list">
            {savedViews.map(sv => (
              <button 
                key={sv.id} 
                className="saved-view-chip"
                onClick={() => handleApplySavedView(sv)}
                title={`Saved Filter View: ${sv.name}`}
              >
                {sv.name}
              </button>
            ))}
            <button 
              className="saved-view-clear" 
              onClick={() => {
                localStorage.removeItem("nexus_saved_views");
                setSavedViews([]);
              }}
              title="Clear saved views"
            >
              Clear
            </button>
          </div>
        </div>
      )}

      {/* Executive KPIs Row */}
      {kpis.length > 0 ? (
        <div className="kpi-grid">
          {kpis.map(k => (
            <div className="kpi-card" key={k.id}>
              <div className="kpi-icon-wrap">
                {getKpiIcon(k.id)}
              </div>
              <div className="kpi-content">
                <span className="kpi-label">{k.label}</span>
                <strong className="kpi-value">{k.formatted || k.value}</strong>
                {k.subtext && <small className="kpi-subtext">{k.subtext}</small>}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty-kpis">
          <AlertCircle size={18} className="text-yellow" />
          <p>{unavail.general || "No business metrics detected in active tables. Upload a structured dataset to compute KPIs."}</p>
        </div>
      )}

      {/* Customizable Interactive Charts Grid */}
      {charts.length > 0 ? (
        <div className="charts-grid">
          {charts.map(chart => (
            <InteractiveChartCard
              key={chart.id}
              id={chart.id}
              title={chart.title}
              subtitle={chart.subtitle || "ANALYTICAL BREAKDOWN"}
              data={chart.data}
              availableMetrics={chart.available_metrics || []}
              defaultMetric={chart.default_metric}
              availableDimensions={chart.available_dimensions || []}
              defaultDimension={chart.default_dimension}
              sym={sym}
              formatMoney={formatMoney}
              onOpenModal={setActiveModalChart}
            />
          ))}
        </div>
      ) : (
        /* Retail / Default Charts Grid Fallback */
        <div className="charts-grid">
          {/* 1. Monthly Sales & Revenue Trend (Only if data exists) */}
          {monthly.length > 0 && (
            <div className="chart-card">
              <div className="chart-header">
                <div>
                  <span className="eyebrow">TIME-SERIES ANALYSIS</span>
                  <h3>Monthly Sales & Revenue Trend</h3>
                </div>
                
                <div className="chart-header-actions">
                  {yearlyComp.length > 0 && selectedYear === null && (
                    <div className="chart-view-toggle">
                      <button 
                        className={`btn-toggle-view ${trendViewMode === "timeline" ? "active" : ""}`}
                        onClick={() => setTrendViewMode("timeline")}
                      >
                        Timeline
                      </button>
                      <button 
                        className={`btn-toggle-view ${trendViewMode === "yoy" ? "active" : ""}`}
                        onClick={() => setTrendViewMode("yoy")}
                      >
                        2025 vs 2026
                      </button>
                    </div>
                  )}
                  <button 
                    className="btn-chart-action" 
                    title="Full-screen view"
                    onClick={() => setActiveModalChart({
                      id: "monthly_trend",
                      title: "Monthly Sales & Revenue Trend",
                      subtitle: "TIME-SERIES ANALYSIS",
                      data: monthly,
                      availableMetrics: ["revenue", "profit", "orders"],
                      defaultMetric: "revenue",
                      availableDimensions: ["month"],
                      defaultDimension: "month",
                      sym,
                      formatMoney
                    })}
                  >
                    <Maximize2 size={14} />
                  </button>
                </div>
              </div>

              <div className="chart-body">
                {trendViewMode === "yoy" && yearlyComp.length > 0 && selectedYear === null ? (
                  <ResponsiveContainer width="100%" height={270}>
                    <BarChart data={yearlyComp} margin={{ top: 15, right: 20, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.6} />
                      <XAxis dataKey="month_name" stroke="var(--text-muted)" fontSize={11} />
                      <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={formatMoney} />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: "var(--bg-card)", 
                          borderColor: "var(--border-color)", 
                          borderRadius: "8px", 
                          color: "var(--text-main)" 
                        }}
                        formatter={(value, name) => [
                          `${sym}${Number(value).toLocaleString()}`, 
                          name === "rev_2025" ? "2025 Revenue" : name === "rev_2026" ? "2026 Revenue" : name
                        ]}
                      />
                      <Legend />
                      <Bar dataKey="rev_2025" name="2025 Revenue" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                      <Bar dataKey="rev_2026" name="2026 Revenue" fill="#10b981" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <ResponsiveContainer width="100%" height={270}>
                    <LineChart data={monthly} margin={{ top: 15, right: 20, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" opacity={0.6} />
                      <XAxis dataKey="month" stroke="var(--text-muted)" fontSize={11} />
                      <YAxis stroke="var(--text-muted)" fontSize={11} tickFormatter={formatMoney} />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: "var(--bg-card)", 
                          borderColor: "var(--border-color)", 
                          borderRadius: "8px", 
                          color: "var(--text-main)" 
                        }}
                        formatter={(value, name) => [
                          `${sym}${Number(value).toLocaleString()}`, 
                          name === "revenue" ? "Revenue" : name === "profit" ? "Profit" : name
                        ]}
                      />
                      <Legend />
                      <Line type="monotone" dataKey="revenue" name="Revenue" stroke="#3b82f6" strokeWidth={2.5} dot={{ r: 3 }} activeDot={{ r: 5 }} />
                      {monthly[0]?.profit !== undefined && (
                        <Line type="monotone" dataKey="profit" name="Profit" stroke="#10b981" strokeWidth={2} dot={{ r: 3 }} />
                      )}
                    </LineChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          )}

          {/* 2. Geographic Performance (Only if data exists) */}
          {regional.length > 0 && (
            <InteractiveChartCard
              id="regional_sales"
              title="Revenue by Region"
              subtitle="GEOGRAPHIC PERFORMANCE"
              data={regional}
              availableMetrics={["revenue", "profit", "orders"]}
              defaultMetric="revenue"
              availableDimensions={["region"]}
              defaultDimension="region"
              sym={sym}
              formatMoney={formatMoney}
              onOpenModal={setActiveModalChart}
            />
          )}

          {/* 3. Category-Wise Performance (Only if data exists) */}
          {categories.length > 0 && (
            <InteractiveChartCard
              id="category_sales"
              title="Category-Wise Performance"
              subtitle="PORTFOLIO MIX"
              data={categories}
              availableMetrics={["revenue", "profit", "orders"]}
              defaultMetric="revenue"
              availableDimensions={["category"]}
              defaultDimension="category"
              sym={sym}
              formatMoney={formatMoney}
              onOpenModal={setActiveModalChart}
            />
          )}

          {/* 4. Top Performing Products Leaderboard (Only if products exist) */}
          {products.length > 0 && (
            <div className="chart-card">
              <div className="chart-header">
                <div>
                  <span className="eyebrow">LEADERBOARD</span>
                  <h3>Top 5 Performing Products (by Net Revenue)</h3>
                </div>
                <div className="chart-header-actions">
                  <button 
                    className="btn-chart-action" 
                    title="Full-screen leaderboard view"
                    onClick={() => setActiveModalChart({
                      id: "top_products_modal",
                      title: "Top Products by Revenue & Profit",
                      subtitle: "PRODUCT LEADERBOARD",
                      data: products,
                      availableMetrics: ["revenue", "profit", "units"],
                      defaultMetric: "revenue",
                      availableDimensions: ["product"],
                      defaultDimension: "product",
                      sym,
                      formatMoney
                    })}
                  >
                    <Maximize2 size={14} />
                  </button>
                </div>
              </div>
              <div className="chart-body leaderboard-body">
                <div className="table-wrap">
                  <table className="products-table">
                    <thead>
                      <tr>
                        <th style={{ width: "45px" }}>Rank</th>
                        <th>Product</th>
                        <th>Units Sold</th>
                        {products[0]?.profit !== undefined && <th>Profit</th>}
                        <th style={{ textAlign: "right" }}>Net Revenue</th>
                      </tr>
                    </thead>
                    <tbody>
                      {products.slice(0, 5).map((p, idx) => (
                        <tr key={idx}>
                          <td>
                            <span className={`rank-badge rank-${p.rank || idx + 1}`}>
                              {p.rank || idx + 1}
                            </span>
                          </td>
                          <td>
                            <b className="prod-name">{p.product}</b>
                          </td>
                          <td>{p.units.toLocaleString()}</td>
                          {p.profit !== undefined && (
                            <td>
                              <span className="profit-badge">{formatMoney(p.profit)}</span>
                            </td>
                          )}
                          <td style={{ textAlign: "right" }}>
                            <span className="rev-badge">{formatMoney(p.revenue)}</span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Full-Screen Interactive Chart Modal */}
      <ChartModal 
        chartConfig={activeModalChart} 
        onClose={() => setActiveModalChart(null)} 
      />
    </div>
  );
}
