import { X, Table2 } from "lucide-react";

export default function DatasetPreviewModal({ preview, onClose }) {
  if (!preview) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-row">
            <Table2 size={18} className="text-blue" />
            <div>
              <h3>Table Preview: {preview.table_name}</h3>
              <small>{preview.total_rows?.toLocaleString()} total rows in DuckDB</small>
            </div>
          </div>
          <button className="btn-close-modal" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          <div className="table-wrap">
            <table className="preview-table">
              <thead>
                <tr>
                  <th>#</th>
                  {preview.columns?.map(col => (
                    <th key={col}>{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows?.map((row, idx) => (
                  <tr key={idx}>
                    <td className="row-num">{idx + 1}</td>
                    {preview.columns?.map(col => (
                      <td key={col}>
                        {row[col] !== null && row[col] !== undefined ? String(row[col]) : "—"}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="modal-footer">
          <span>Showing preview sample up to {preview.rows?.length} rows</span>
          <button className="btn-done" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
