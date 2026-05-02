import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Filter,
  Plus,
  Trash2,
  Edit,
  Save,
  X,
  Loader2,
  Link as LinkIcon,
} from 'lucide-react';
import { api, queryKeys, type Source, type Selector } from '../../api';

interface SelectorsPanelProps {
  workspaceDir: string;
  selectors: Selector[];
  sources: Source[];
  onRefresh: () => void;
}

export function SelectorsPanel({ workspaceDir, selectors, sources, onRefresh }: SelectorsPanelProps) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSelector, setEditingSelector] = useState<Selector | null>(null);
  const queryClient = useQueryClient();

  const createSelector = useMutation({
    mutationFn: (selector: Partial<Selector>) =>
      api.selectors.create({ workspace_dir: workspaceDir, ...selector }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.sources.all(workspaceDir) });
      setShowAddModal(false);
    },
  });

  const deleteSelector = useMutation({
    mutationFn: (name: string) => api.selectors.delete(name, workspaceDir),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: queryKeys.sources.all(workspaceDir) }),
  });

  return (
    <div className="config-panel">
      <div className="panel-header">
        <h3>Selectors</h3>
        <button className="primary-button" onClick={() => setShowAddModal(true)}>
          <Plus size={16} /> Add Selector
        </button>
      </div>

      <div className="config-list">
        {selectors.map((selector) => {
          const source = sources.find(s => s.name === selector.source);
          return (
            <div key={selector.name} className="config-item">
              <div className="config-item-header">
                <div className="config-item-title">
                  <Filter size={18} />
                  <strong>{selector.name}</strong>
                  <span className="link-badge">
                    <LinkIcon size={12} /> {selector.source}
                  </span>
                </div>
                <div className="config-item-actions">
                  <button onClick={() => setEditingSelector(selector)}>
                    <Edit size={14} /> Edit
                  </button>
                  <button onClick={() => deleteSelector.mutate(selector.name)} className="danger">
                    <Trash2 size={14} /> Delete
                  </button>
                </div>
              </div>
              <div className="config-item-details">
                <div className="detail-row">
                  <span>Source Kind:</span>
                  <span>{source?.kind || 'unknown'}</span>
                </div>
                {selector.selector && (
                  <div className="detail-row">
                    <span>Type:</span>
                    <span>{String((selector.selector as any).type || '-')}</span>
                  </div>
                )}
                {(selector.selector as any)?.project_key && (
                  <div className="detail-row">
                    <span>Project:</span>
                    <span>{String((selector.selector as any).project_key)}</span>
                  </div>
                )}
                {(selector.selector as any)?.space_key && (
                  <div className="detail-row">
                    <span>Space:</span>
                    <span>{String((selector.selector as any).space_key)}</span>
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {showAddModal && (
        <SelectorFormModal
          workspaceDir={workspaceDir}
          sources={sources}
          onClose={() => setShowAddModal(false)}
          onSubmit={(selector) => createSelector.mutate(selector)}
          isSubmitting={createSelector.isPending}
        />
      )}

      {editingSelector && (
        <SelectorFormModal
          workspaceDir={workspaceDir}
          sources={sources}
          selector={editingSelector}
          onClose={() => setEditingSelector(null)}
          onSubmit={(selector) => createSelector.mutate(selector)}
          isSubmitting={createSelector.isPending}
        />
      )}
    </div>
  );
}

interface SelectorFormModalProps {
  workspaceDir: string;
  sources: Source[];
  selector?: Selector;
  onClose: () => void;
  onSubmit: (selector: Partial<Selector>) => void;
  isSubmitting: boolean;
}

function SelectorFormModal({
  workspaceDir,
  sources,
  selector,
  onClose,
  onSubmit,
  isSubmitting
}: SelectorFormModalProps) {
  const [formData, setFormData] = useState({
    name: selector?.name || '',
    source: selector?.source || sources[0]?.name || '',
    type: (selector?.selector as any)?.type || 'project_slice',
    project_key: (selector?.selector as any)?.project_key || '',
    space_key: (selector?.selector as any)?.space_key || '',
    file_path: (selector?.selector as any)?.path || '',
  });

  const selectedSource = sources.find(s => s.name === formData.source);
  const sourceKind = selectedSource?.kind || 'jira';

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    let selectorConfig: any = { type: formData.type };

    if (sourceKind === 'jira' && formData.project_key) {
      selectorConfig.project_key = formData.project_key;
    } else if (sourceKind === 'confluence' && formData.space_key) {
      selectorConfig.space_key = formData.space_key;
    } else if (sourceKind === 'pdf' && formData.file_path) {
      selectorConfig.path = formData.file_path;
    }

    onSubmit({
      name: formData.name,
      source: formData.source,
      selector: selectorConfig,
    } as any);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>{selector ? 'Edit Selector' : 'Add Selector'}</h3>
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
              placeholder="demo_jira_project"
              required
            />
          </label>

          <label>
            Source
            <select
              value={formData.source}
              onChange={(e) => setFormData({ ...formData, source: e.target.value })}
              required
            >
              {sources.map((source) => (
                <option key={source.name} value={source.name}>
                  {source.name} ({source.kind})
                </option>
              ))}
            </select>
          </label>

          <label>
            Selector Type
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
            >
              {sourceKind === 'jira' && (
                <>
                  <option value="issue">Issue</option>
                  <option value="project_slice">Project Slice</option>
                  <option value="project_full">Project Full</option>
                </>
              )}
              {sourceKind === 'confluence' && (
                <>
                  <option value="page">Page</option>
                  <option value="page_tree">Page Tree</option>
                  <option value="space_slice">Space Slice</option>
                </>
              )}
              {sourceKind === 'pdf' && (
                <option value="file">File</option>
              )}
            </select>
          </label>

          {sourceKind === 'jira' && (
            <label>
              Project Key
              <input
                type="text"
                value={formData.project_key}
                onChange={(e) => setFormData({ ...formData, project_key: e.target.value })}
                placeholder="SSD"
              />
            </label>
          )}

          {sourceKind === 'confluence' && (
            <label>
              Space Key
              <input
                type="text"
                value={formData.space_key}
                onChange={(e) => setFormData({ ...formData, space_key: e.target.value })}
                placeholder="TEAM"
              />
            </label>
          )}

          {sourceKind === 'pdf' && (
            <label>
              File Path
              <input
                type="text"
                value={formData.file_path}
                onChange={(e) => setFormData({ ...formData, file_path: e.target.value })}
                placeholder="path/to/file.pdf"
              />
            </label>
          )}

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
