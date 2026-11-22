import { useState } from "react";
import { Scissors, CheckCircle2, FileText, X, UploadCloud } from "lucide-react";

export default function LargeFileSplitModal({
  file,
  onClose,
  onSplitAndUpload,
  onUploadSingle
}) {
  const [chunkSizeMb, setChunkSizeMb] = useState(25);
  const [splitting, setSplitting] = useState(false);

  if (!file) return null;

  const fileSizeMb = (file.size / (1024 * 1024)).toFixed(1);
  const estimatedParts = Math.ceil(file.size / (chunkSizeMb * 1024 * 1024));

  const lastDot = file.name.lastIndexOf(".");
  const baseName = lastDot !== -1 ? file.name.substring(0, lastDot) : file.name;
  const ext = lastDot !== -1 ? file.name.substring(lastDot) : "";

  const handleConfirmSplit = async () => {
    setSplitting(true);
    try {
      await onSplitAndUpload(file, chunkSizeMb);
      onClose();
    } catch {
    } finally {
      setSplitting(false);
    }
  };

  const handleConfirmSingle = async () => {
    setSplitting(true);
    try {
      await onUploadSingle(file);
      onClose();
    } catch {
    } finally {
      setSplitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog split-modal-card" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <div className="split-modal-title-row">
            <div className="split-icon-badge">
              <Scissors size={18} />
            </div>
            <div>
              <h3>Large File Chunking &amp; Splitting</h3>
              <p className="split-subtitle">File exceeds standard 50 MB threshold</p>
            </div>
          </div>
          <button className="btn-close-modal" onClick={onClose} title="Cancel">
            <X size={16} />
          </button>
        </div>

        <div className="modal-body">
          {/* File details card */}
          <div className="split-file-info-card">
            <div className="split-file-left">
              <FileText size={24} className="text-blue" />
              <div>
                <strong className="split-file-name" title={file.name}>{file.name}</strong>
                <div className="split-file-size-badge">
                  <span>{fileSizeMb} MB</span>
                  <span className="badge-warning">Exceeds 50 MB limit</span>
                </div>
              </div>
            </div>
          </div>

          <p className="split-description">
            To prevent browser timeouts and ensure seamless DuckDB ingestion, NEXUS AI can automatically 
            split this dataset into <strong>{estimatedParts} balanced parts</strong>. Table headers are 
            preserved on every part so you can query across all chunks simultaneously.
          </p>

          {/* Chunk size configuration */}
          <div className="split-options-group">
            <label className="split-option-label">Select Target Part Size:</label>
            <div className="split-buttons-toggle">
              <button
                type="button"
                className={`btn-chunk-size ${chunkSizeMb === 25 ? "active" : ""}`}
                onClick={() => setChunkSizeMb(25)}
              >
                <strong>25 MB / part</strong>
                <small>Recommended (~{Math.ceil(file.size / (25 * 1024 * 1024))} parts)</small>
              </button>
              <button
                type="button"
                className={`btn-chunk-size ${chunkSizeMb === 40 ? "active" : ""}`}
                onClick={() => setChunkSizeMb(40)}
              >
                <strong>40 MB / part</strong>
                <small>Fewer parts (~{Math.ceil(file.size / (40 * 1024 * 1024))} parts)</small>
              </button>
            </div>
          </div>

          {/* Preview of generated parts */}
          <div className="split-preview-box">
            <span className="split-preview-title">Generated Parts Preview:</span>
            <div className="split-preview-list">
              {Array.from({ length: Math.min(estimatedParts, 5) }).map((_, idx) => (
                <div className="split-preview-item" key={idx}>
                  <CheckCircle2 size={13} className="text-emerald" />
                  <span className="preview-part-name">
                    {baseName}_part_{idx + 1}{ext}
                  </span>
                  <span className="preview-part-size">
                    ~{idx === estimatedParts - 1 
                      ? (file.size % (chunkSizeMb * 1024 * 1024) / (1024 * 1024) || chunkSizeMb).toFixed(1) 
                      : chunkSizeMb} MB
                  </span>
                </div>
              ))}
              {estimatedParts > 5 && (
                <div className="split-preview-more">
                  + {estimatedParts - 5} more parts...
                </div>
              )}
            </div>
          </div>

          <div className="split-tip-note">
            <CheckCircle2 size={13} className="text-emerald" />
            <span>CSV headers are automatically replicated across each part for cross-file queries.</span>
          </div>
        </div>

        <div className="modal-footer split-modal-footer">
          <button 
            type="button" 
            className="btn-modal-secondary" 
            onClick={onClose}
            disabled={splitting}
          >
            Cancel
          </button>
          
          <button
            type="button"
            className="btn-modal-outline"
            onClick={handleConfirmSingle}
            disabled={splitting}
            title="Upload as a single file up to 150MB"
          >
            <UploadCloud size={14} /> Upload As-Is
          </button>

          <button
            type="button"
            className="btn-modal-primary"
            onClick={handleConfirmSplit}
            disabled={splitting}
          >
            {splitting ? (
              <>Splitting &amp; Uploading…</>
            ) : (
              <>
                <Scissors size={14} /> Split &amp; Upload {estimatedParts} Parts
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
