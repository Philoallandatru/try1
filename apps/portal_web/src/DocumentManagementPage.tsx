import { useState, useEffect } from "react";
import { Upload, FileText, Trash2, Filter, CheckCircle, AlertCircle, Loader2 } from "lucide-react";

interface DocumentAsset {
  doc_id: string;
  display_name: string;
  document_type: string;
  version: string;
  document_id: string;
  created_at: string;
  file_size: number;
  original_filename: string;
}

interface DocumentType {
  priority: number;
  label: string;
}

interface DocumentManagementPageProps {
  workspaceDir: string;
}

export function DocumentManagementPage({ workspaceDir }: DocumentManagementPageProps) {
  // Extract workspace name from full path (e.g., ".tmp\portal-runner\workspaces\demo" -> "demo")
  const workspaceName = workspaceDir.split(/[/\\]/).pop() || workspaceDir;

  const [documents, setDocuments] = useState<DocumentAsset[]>([]);
  const [documentTypes, setDocumentTypes] = useState<Record<string, DocumentType>>({});
  const [loading, setLoading] = useState(false);
  const [filterType, setFilterType] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<{ type: "success" | "error" | "processing"; message: string } | null>(null);
  const [processingTaskId, setProcessingTaskId] = useState<string | null>(null);

  // Upload form state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploadType, setUploadType] = useState<string>("other");
  const [displayName, setDisplayName] = useState<string>("");
  const [isDragging, setIsDragging] = useState(false);

  useEffect(() => {
    loadDocumentTypes();
    loadDocuments();
  }, [workspaceDir, filterType]);

  // Poll task status if we have a processing task
  useEffect(() => {
    if (!processingTaskId) return;

    const pollInterval = setInterval(async () => {
      try {
        const token = localStorage.getItem("ssdPortalToken") || "";
        const response = await fetch(`/api/documents/task/${processingTaskId}`, {
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        });
        const taskStatus = await response.json();

        if (taskStatus.status === "completed") {
          setUploadStatus({ type: "success", message: "Document processed and indexed successfully!" });
          setProcessingTaskId(null);
          loadDocuments();
        } else if (taskStatus.status === "failed") {
          setUploadStatus({ type: "error", message: `Processing failed: ${taskStatus.error || "Unknown error"}` });
          setProcessingTaskId(null);
        } else if (taskStatus.status === "processing") {
          setUploadStatus({ type: "processing", message: "Processing document and updating search index..." });
        }
      } catch (error) {
        console.error("Failed to poll task status:", error);
      }
    }, 2000); // Poll every 2 seconds

    return () => clearInterval(pollInterval);
  }, [processingTaskId]);

  const loadDocumentTypes = async () => {
    try {
      const token = localStorage.getItem("ssdPortalToken") || "";
      const response = await fetch("/api/documents/types", {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      const data = await response.json();
      if (data.success) {
        setDocumentTypes(data.types);
      }
    } catch (error) {
      console.error("Failed to load document types:", error);
    }
  };

  const loadDocuments = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem("ssdPortalToken") || "";
      const url = filterType
        ? `/api/documents/list?workspace=${encodeURIComponent(workspaceName)}&document_type=${filterType}`
        : `/api/documents/list?workspace=${encodeURIComponent(workspaceName)}`;
      const response = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {}
      });
      const data = await response.json();
      if (data.success) {
        setDocuments(data.documents);
      }
    } catch (error) {
      console.error("Failed to load documents:", error);
    } finally {
      setLoading(false);
    }
  };

  const handleFileSelect = (file: File) => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setUploadStatus({ type: "error", message: "Only PDF files are supported" });
      return;
    }
    setSelectedFile(file);
    if (!displayName) {
      setDisplayName(file.name.replace(/\.pdf$/i, ''));
    }
    setUploadStatus(null);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      handleFileSelect(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadStatus({ type: "error", message: "Please select a file" });
      return;
    }

    setLoading(true);
    setUploadStatus({ type: "processing", message: "Uploading file..." });

    try {
      const formData = new FormData();
      formData.append("workspace", workspaceName);
      formData.append("file", selectedFile);
      formData.append("document_type", uploadType);
      if (displayName) {
        formData.append("display_name", displayName);
      }

      const token = localStorage.getItem("ssdPortalToken") || "";
      const response = await fetch("/api/documents/upload", {
        method: "POST",
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: formData,
      });

      const data = await response.json();

      if (data.success) {
        if (data.task_id) {
          // Async processing - start polling
          setProcessingTaskId(data.task_id);
          setUploadStatus({ type: "processing", message: "File uploaded, processing document..." });
        } else {
          // Sync processing completed
          setUploadStatus({ type: "success", message: "Document uploaded successfully!" });
          loadDocuments();
        }
        setSelectedFile(null);
        setDisplayName("");
      } else {
        setUploadStatus({ type: "error", message: data.detail || "Upload failed" });
      }
    } catch (error) {
      setUploadStatus({ type: "error", message: `Upload failed: ${error}` });
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    if (!confirm(`Are you sure you want to delete document "${docId}"?`)) {
      return;
    }

    try {
      const token = localStorage.getItem("ssdPortalToken") || "";
      const response = await fetch(
        `/api/documents/delete?workspace=${encodeURIComponent(workspaceName)}&doc_id=${encodeURIComponent(docId)}`,
        {
          method: "DELETE",
          headers: token ? { Authorization: `Bearer ${token}` } : {}
        }
      );
      const data = await response.json();
      if (data.success) {
        setUploadStatus({ type: "success", message: data.message });
        loadDocuments();
      } else {
        setUploadStatus({ type: "error", message: "Delete failed" });
      }
    } catch (error) {
      setUploadStatus({ type: "error", message: `Delete failed: ${error}` });
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="document-management-page">
      <div className="page-header">
        <h1><FileText size={24} /> Document Management</h1>
        <p>Upload and manage documents for retrieval (Spec, Policy, Other)</p>
      </div>

      {uploadStatus && (
        <div className={`status-message ${uploadStatus.type}`}>
          {uploadStatus.type === "success" && <CheckCircle size={20} />}
          {uploadStatus.type === "error" && <AlertCircle size={20} />}
          {uploadStatus.type === "processing" && <Loader2 size={20} className="spinner" />}
          <span>{uploadStatus.message}</span>
        </div>
      )}

      <div className="upload-section">
        <h2>Upload Document</h2>
        <div
          className={`upload-dropzone ${isDragging ? "dragging" : ""}`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <Upload size={48} />
          <p>Drag and drop a PDF file here, or click to select</p>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => e.target.files?.[0] && handleFileSelect(e.target.files[0])}
            style={{ display: "none" }}
            id="file-input"
          />
          <label htmlFor="file-input" className="file-select-button">
            Select PDF File
          </label>
        </div>

        {selectedFile && (
          <div className="upload-form">
            <div className="form-group">
              <label>Selected File:</label>
              <div className="file-info">
                <FileText size={20} />
                <span>{selectedFile.name}</span>
                <span className="file-size">({formatFileSize(selectedFile.size)})</span>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="document-type">Document Type:</label>
              <select
                id="document-type"
                value={uploadType}
                onChange={(e) => setUploadType(e.target.value)}
              >
                {Object.entries(documentTypes).map(([key, type]) => (
                  <option key={key} value={key}>
                    {type.label} (Priority: {type.priority})
                  </option>
                ))}
              </select>
              <small>
                Spec documents have highest priority in retrieval, followed by Policy, then Other
              </small>
            </div>

            <div className="form-group">
              <label htmlFor="display-name">Display Name (optional):</label>
              <input
                id="display-name"
                type="text"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                placeholder="Leave empty to use filename"
              />
            </div>

            <button
              className="upload-button"
              onClick={handleUpload}
              disabled={loading}
            >
              {loading ? "Uploading..." : "Upload Document"}
            </button>
          </div>
        )}
      </div>

      <div className="documents-section">
        <div className="section-header">
          <h2>Uploaded Documents ({documents.length})</h2>
          <div className="filter-controls">
            <Filter size={20} />
            <select
              value={filterType || ""}
              onChange={(e) => setFilterType(e.target.value || null)}
            >
              <option value="">All Types</option>
              {Object.entries(documentTypes).map(([key, type]) => (
                <option key={key} value={key}>
                  {type.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {loading && documents.length === 0 ? (
          <div className="loading-state">Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className="empty-state">
            <FileText size={48} />
            <p>No documents uploaded yet</p>
            <p>Upload your first document to get started</p>
          </div>
        ) : (
          <div className="documents-list">
            {documents.map((doc) => (
              <div key={doc.doc_id} className="document-card">
                <div className="document-header">
                  <FileText size={24} />
                  <div className="document-info">
                    <h3>{doc.display_name}</h3>
                    <div className="document-meta">
                      <span className={`type-badge ${doc.document_type}`}>
                        {documentTypes[doc.document_type]?.label || doc.document_type}
                      </span>
                      <span className="version">v{doc.version}</span>
                      <span className="file-size">{formatFileSize(doc.file_size)}</span>
                    </div>
                  </div>
                </div>
                <div className="document-details">
                  <div className="detail-row">
                    <span className="label">Original File:</span>
                    <span>{doc.original_filename}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Document ID:</span>
                    <span className="mono">{doc.document_id}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Uploaded:</span>
                    <span>{formatDate(doc.created_at)}</span>
                  </div>
                </div>
                <div className="document-actions">
                  <button
                    className="delete-button"
                    onClick={() => handleDelete(doc.doc_id)}
                    title="Delete document"
                  >
                    <Trash2 size={16} />
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <style>{`
        .document-management-page {
          padding: 2rem;
          max-width: 1200px;
          margin: 0 auto;
        }

        .page-header {
          margin-bottom: 2rem;
        }

        .page-header h1 {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.5rem;
        }

        .status-message {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 1rem;
          border-radius: 8px;
          margin-bottom: 1rem;
        }

        .status-message.success {
          background: #d4edda;
          color: #155724;
          border: 1px solid #c3e6cb;
        }

        .status-message.error {
          background: #f8d7da;
          color: #721c24;
          border: 1px solid #f5c6cb;
        }

        .status-message.processing {
          background: #d1ecf1;
          color: #0c5460;
          border: 1px solid #bee5eb;
        }

        .spinner {
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }

        .upload-section, .documents-section {
          background: white;
          border-radius: 12px;
          padding: 1.5rem;
          margin-bottom: 2rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .upload-dropzone {
          border: 2px dashed #ccc;
          border-radius: 8px;
          padding: 3rem;
          text-align: center;
          cursor: pointer;
          transition: all 0.3s;
        }

        .upload-dropzone:hover, .upload-dropzone.dragging {
          border-color: #007bff;
          background: #f0f8ff;
        }

        .upload-dropzone svg {
          color: #999;
          margin-bottom: 1rem;
        }

        .file-select-button {
          display: inline-block;
          padding: 0.5rem 1rem;
          background: #007bff;
          color: white;
          border-radius: 6px;
          cursor: pointer;
          margin-top: 1rem;
        }

        .file-select-button:hover {
          background: #0056b3;
        }

        .upload-form {
          margin-top: 1.5rem;
          padding-top: 1.5rem;
          border-top: 1px solid #eee;
        }

        .form-group {
          margin-bottom: 1.5rem;
        }

        .form-group label {
          display: block;
          font-weight: 600;
          margin-bottom: 0.5rem;
        }

        .form-group input, .form-group select {
          width: 100%;
          padding: 0.75rem;
          border: 1px solid #ddd;
          border-radius: 6px;
          font-size: 1rem;
        }

        .form-group small {
          display: block;
          margin-top: 0.5rem;
          color: #666;
          font-size: 0.875rem;
        }

        .file-info {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem;
          background: #f8f9fa;
          border-radius: 6px;
        }

        .file-size {
          color: #666;
          font-size: 0.875rem;
        }

        .upload-button {
          width: 100%;
          padding: 1rem;
          background: #28a745;
          color: white;
          border: none;
          border-radius: 6px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
        }

        .upload-button:hover:not(:disabled) {
          background: #218838;
        }

        .upload-button:disabled {
          background: #ccc;
          cursor: not-allowed;
        }

        .section-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 1.5rem;
        }

        .filter-controls {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .filter-controls select {
          padding: 0.5rem;
          border: 1px solid #ddd;
          border-radius: 6px;
        }

        .documents-list {
          display: grid;
          gap: 1rem;
        }

        .document-card {
          border: 1px solid #e0e0e0;
          border-radius: 8px;
          padding: 1.5rem;
          transition: box-shadow 0.3s;
        }

        .document-card:hover {
          box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }

        .document-header {
          display: flex;
          gap: 1rem;
          margin-bottom: 1rem;
        }

        .document-info h3 {
          margin: 0 0 0.5rem 0;
        }

        .document-meta {
          display: flex;
          gap: 0.75rem;
          flex-wrap: wrap;
        }

        .type-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
          text-transform: uppercase;
        }

        .type-badge.spec {
          background: #e3f2fd;
          color: #1976d2;
        }

        .type-badge.policy {
          background: #fff3e0;
          color: #f57c00;
        }

        .type-badge.other {
          background: #f5f5f5;
          color: #616161;
        }

        .version, .file-size {
          color: #666;
          font-size: 0.875rem;
        }

        .document-details {
          margin: 1rem 0;
          padding: 1rem;
          background: #f8f9fa;
          border-radius: 6px;
        }

        .detail-row {
          display: flex;
          justify-content: space-between;
          padding: 0.5rem 0;
        }

        .detail-row .label {
          font-weight: 600;
          color: #666;
        }

        .mono {
          font-family: monospace;
          font-size: 0.875rem;
        }

        .document-actions {
          display: flex;
          gap: 0.5rem;
          justify-content: flex-end;
        }

        .delete-button {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.5rem 1rem;
          background: #dc3545;
          color: white;
          border: none;
          border-radius: 6px;
          cursor: pointer;
        }

        .delete-button:hover {
          background: #c82333;
        }

        .empty-state, .loading-state {
          text-align: center;
          padding: 3rem;
          color: #666;
        }

        .empty-state svg {
          color: #ccc;
          margin-bottom: 1rem;
        }
      `}</style>
    </div>
  );
}
