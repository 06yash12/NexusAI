import { X } from "lucide-react";
import InteractiveChartCard from "./InteractiveChartCard";

export default function ChartModal({ chartConfig, onClose }) {
  if (!chartConfig) return null;

  return (
    <div className="chart-modal-backdrop" onClick={onClose}>
      <div className="chart-modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="chart-modal-header">
          <div>
            <span className="eyebrow">{chartConfig.subtitle || "FULL SCREEN VIEW"}</span>
            <h2>{chartConfig.title}</h2>
          </div>
          <button className="btn-close-modal" onClick={onClose} title="Close full screen view">
            <X size={20} />
          </button>
        </div>

        <div className="chart-modal-content">
          <InteractiveChartCard
            {...chartConfig}
            isModal={true}
          />
        </div>
      </div>
    </div>
  );
}
