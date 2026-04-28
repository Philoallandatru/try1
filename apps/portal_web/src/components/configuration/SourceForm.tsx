import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Database,
  Plus,
  Trash2,
  Edit,
  Save,
  X,
  Loader2,
} from 'lucide-react';
import { api, queryKeys, type Source } from '../../api';

interface SourcesPanelProps {
  workspaceDir: string;
  sources: Source[];
  onRefresh: () => void;
}

export function SourcesPanel({ workspaceDir, sources, onRefresh }: SourcesPanelProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const queryClient = useQueryClient();

  const createSource = useMutation({
    mutationFn: (source: Partial<Source>) =>
      api.sources.create({ workspace_dir: workspaceDir, ...source }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.all(workspaceDir) });
      setShowAddModal(false);
    },
  });

  const updateSource = useMutation({
    mutationFn: ({ name, data }: { name: string; data: Partial<Source> }) =>
      api.sources.update(name, { workspace_dir: workspaceDir, ...data }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.all(workspaceDir) });
      setEditingSource(null);
    },
  });

  const deleteSource = useMutation({
    mutationFn: (name: string) => api.sources.delete(name, workspaceDir),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.sources.all(workspaceDir) }),
  });

  return (
    <div className="config-panel">
      <div className="panel-header">
        <h3>Data Sources</h3>
        <button className="primary-button" onClick={() => setShowAddModal(true)}>
          <Plus size={16} /> Add Source
        </button>
      </div>

      <div className="config-list">
        {sources.map((source) => (
          <div key={source.name} className="config-item">
            <div className="config-item-header">
              <div className="config-item-title">
                <Database size={18} />
                <strong>{source.name}</strong>
                <span className="badge">{source.kind}</span>
                <span className={`status-badge ${source.enabled !== false ? 'active' : 'inactive'}`}>
                  {source.enabled !== false ? 'Enabled' : 'Disabled'}
                </span>
              </div>
              <div className="config-item-actions">
                <button onClick={() => setEditingSource(source)}>
                  <Edit size={14} /> Edit
                </button>
                <button onClick={() => deleteSource.mutate(source.name)} className="danger">
                  <Trash2 size={14} /> Delete
                </button>
              </div>
            </div>
            <div className="config-item-details">
              <div className="detail-row">
                <span>Mode:</span>
                <span>{source.mode || 'live'}</span>
              </div>
              <div className="detail-row">
                <span>Connector:</span>
                <span>{source.connector_type}</span>
              </div>
              {source.policies && source.policies.length > 0 && (
                <div className="detail-row">
                  <span>Policies:</span>
                  <span>{source.policies.join(', ')}</span>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {showAddModal && (
        <SourceFormModal
          workspaceDir={workspaceDir}
          onClose={() => setShowAddModal(false)}
          onSubmit={(source) => createSource.mutate(source)}
          isSubmitting={createSource.isPending}
        />
      )}

      {editingSource && (
        <SourceFormModal
          workspaceDir={workspaceDir}
          source={editingSource}
          onClose={() => setEditingSource(null)}
          onSubmit={(source) => updateSource.mutate({ name: editingSource.name, data: source })}
          isSubmitting={updateSource.isPending}
        />
      )}
    </div>
  );
}

interface SourceFormModalProps {
  workspaceDir: string;
  source?: Source;
  onClose: () => void;
  onSubmit: (source: Partial<Source>) => void;
  isSubmitting: boolean;
}

function SourceFormModal({
  workspaceDir,
  source,
  onClose,
  onSubmit,
  isSubmitting
}: SourceFormModalProps) {
  const [formData, setFormData] = useState({
    name: source?.name || '',
    kind: source?.kind || 'jira',
    mode: source?.mode || 'fixture',
    connector_type: source?.connector_type || 'jira.atlassian_api',
    enabled: source?.enabled !== false,
    config_path: '',
    policies: source?.policies?.join(', ') || 'team:ssd, public',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const payload: any = {
      name: formData.name,
      kind: formData.kind,
      mode: formData.mode,
      connector_type: formData.connector_type,
      enabled: formData.enabled,
      config: {},
      policies: formData.policies.split(',').map(p => p.trim()).filter(Boolean),
      metadata: { description: `${formData.kind} source` },
    };
    if (formData.config_path) {
      payload.path = formData.config_path;
    }
    onSubmit(payload);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{source ? 'Edit Source' : 'Add Source'}</h3>
          <button onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <label>
            Name
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="demo_jira"
              required
            />
          </label>

          <label>
            Kind
            <select
              value={formData.kind}
              onChange={(e) => {
                const kind = e.target.value;
                setFormData({
                  ...formData,
                  kind,
                  connector_type: kind === 'jira' ? 'jira.atlassian_api' :
                                 kind === 'confluence' ? 'confluence.atlassian_api' :
                                 'pdf.local_file'
                });
              }}
            >
              <option value="jira">Jira</option>
              <option value="confluence">Confluence</option>
              <option value="pdf">PDF</option>
            </select>
          </label>

          <label>
            Mode
            <select
              value={formData.mode}
              onChange={(e) => setFormData({ ...formData, mode: e.target.value })}
            >
              <option value="fixture">Fixture</option>
              <option value="live">Live</option>
              <option value="local">Local</option>
            </select>
          </label>

          <label>
            Connector Type
            <input
              type="text"
              value={formData.connector_type}
              onChange={(e) => setFormData({ ...formData, connector_type: e.target.value })}
              readOnly
            />
          </label>

          {formData.mode === 'fixture' && (
            <label>
              Config Path (fixture file)
              <input
                type="text"
                value={formData.config_path}
                onChange={(e) => setFormData({ ...formData, config_path: e.target.value })}
                placeholder="fixtures/demo/jira/data.json"
              />
            </label>
          )}

          <label>
            Policies (comma-separated)
            <input
              type="text"
              value={formData.policies}
              onChange={(e) => setFormData({ ...formData, policies: e.target.value })}
              placeholder="team:ssd, public"
            />
          </label>

          <label className="checkbox-label">
            <input
              type="checkbox"
              checked={formData.enabled}
              onChange={(e) => setFormData({ ...formData, enabled: e.target.checked })}
            />
            Enabled
          </label>

          <div className="modal-actions">
            <button type="button" onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" disabled={isSubmitting} className="primary-button">
              {isSubmitting ? <><Loader2 size={16} className="spin" /> Saving...</> : <><Save size={16} /> Save</>}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
