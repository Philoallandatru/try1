import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { z } from 'zod';
import {
  Database,
  Filter,
  Settings,
  Plus,
  Trash2,
  Edit,
  Save,
  X,
  CheckCircle,
  AlertCircle,
  Loader2,
  Copy,
  FileText,
  Link as LinkIcon
} from 'lucide-react';
import { apiJson } from './apiUtils';

// Schemas
const sourceSchema = z.object({
  name: z.string(),
  kind: z.string(),
  connector_type: z.string(),
  mode: z.string().optional(),
  enabled: z.boolean().optional(),
  config: z.record(z.string(), z.unknown()).optional(),
  defaults: z.record(z.string(), z.unknown()).optional(),
  policies: z.array(z.string()).optional(),
  metadata: z.record(z.string(), z.unknown()).optional(),
});

const selectorSchema = z.object({
  name: z.string(),
  source: z.string(),
  selector: z.record(z.string(), z.unknown()).optional(),
});

const profileSchema = z.object({
  name: z.string(),
  inputs: z.record(z.string(), z.unknown()).optional(),
  analysis: z.record(z.string(), z.unknown()).optional(),
});

const sourcesResponseSchema = z.object({
  sources: z.array(sourceSchema),
  selectors: z.array(selectorSchema).default([]),
});

const profilesResponseSchema = z.object({
  profiles: z.array(profileSchema),
});

type Source = z.infer<typeof sourceSchema>;
type Selector = z.infer<typeof selectorSchema>;
type Profile = z.infer<typeof profileSchema>;

interface ConfigurationPageProps {
  workspaceDir: string;
}

type TabType = 'sources' | 'selectors' | 'profiles';

export default function ConfigurationPage({ workspaceDir }: ConfigurationPageProps) {
  const [activeTab, setActiveTab] = useState<TabType>('sources');
  const queryClient = useQueryClient();

  const sources = useQuery({
    queryKey: ['sources', workspaceDir],
    queryFn: () => apiJson(`/api/workspace/sources?workspace_dir=${encodeURIComponent(workspaceDir)}`, sourcesResponseSchema),
    enabled: Boolean(workspaceDir),
  });

  const profiles = useQuery({
    queryKey: ['profiles', workspaceDir],
    queryFn: () => apiJson(`/api/workspace/profiles?workspace_dir=${encodeURIComponent(workspaceDir)}`, profilesResponseSchema),
    enabled: Boolean(workspaceDir),
  });

  const sourcesData = sources.data?.sources || [];
  const selectorsData = sources.data?.selectors || [];
  const profilesData = profiles.data?.profiles || [];

  return (
    <section className="page-grid">
      <div className="primary-surface">
        <div className="section-heading">
          <p className="eyebrow">Configuration</p>
          <h2>Workspace Configuration</h2>
          <p>Manage data sources, selectors, and analysis profiles</p>
        </div>

        <div className="config-tabs">
          <button
            className={activeTab === 'sources' ? 'config-tab active' : 'config-tab'}
            onClick={() => setActiveTab('sources')}
          >
            <Database size={16} /> Sources ({sourcesData.length})
          </button>
          <button
            className={activeTab === 'selectors' ? 'config-tab active' : 'config-tab'}
            onClick={() => setActiveTab('selectors')}
          >
            <Filter size={16} /> Selectors ({selectorsData.length})
          </button>
          <button
            className={activeTab === 'profiles' ? 'config-tab active' : 'config-tab'}
            onClick={() => setActiveTab('profiles')}
          >
            <Settings size={16} /> Profiles ({profilesData.length})
          </button>
        </div>

        {activeTab === 'sources' && (
          <SourcesPanel
            workspaceDir={workspaceDir}
            sources={sourcesData}
            onRefresh={() => queryClient.invalidateQueries({ queryKey: ['sources', workspaceDir] })}
          />
        )}

        {activeTab === 'selectors' && (
          <SelectorsPanel
            workspaceDir={workspaceDir}
            selectors={selectorsData}
            sources={sourcesData}
            onRefresh={() => queryClient.invalidateQueries({ queryKey: ['sources', workspaceDir] })}
          />
        )}

        {activeTab === 'profiles' && (
          <ProfilesPanel
            workspaceDir={workspaceDir}
            profiles={profilesData}
            sources={sourcesData}
            selectors={selectorsData}
            onRefresh={() => queryClient.invalidateQueries({ queryKey: ['profiles', workspaceDir] })}
          />
        )}
      </div>

      <aside className="side-panel">
        <h3>Configuration Guide</h3>
        <div className="guide-content">
          <div className="guide-section">
            <strong>1. Sources</strong>
            <p>Define data sources (Jira, Confluence, PDF) with connection details</p>
          </div>
          <div className="guide-section">
            <strong>2. Selectors</strong>
            <p>Create selectors to filter data from sources (projects, spaces, files)</p>
          </div>
          <div className="guide-section">
            <strong>3. Profiles</strong>
            <p>Combine sources and selectors into reusable analysis profiles</p>
          </div>
          <div className="guide-section">
            <strong>Relationship</strong>
            <p>Profile → Selector → Source</p>
          </div>
        </div>
      </aside>
    </section>
  );
}

function SourcesPanel({ workspaceDir, sources, onRefresh }: {
  workspaceDir: string;
  sources: Source[];
  onRefresh: () => void;
}) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSource, setEditingSource] = useState<Source | null>(null);
  const queryClient = useQueryClient();

  const createSource = useMutation({
    mutationFn: (source: Partial<Source>) =>
      apiJson('/api/workspace/sources', z.unknown(), {
        method: 'POST',
        body: JSON.stringify({ workspace_dir: workspaceDir, ...source }),
      }),
    onSuccess: () => {
      onRefresh();
      setShowAddModal(false);
    },
  });

  const deleteSource = useMutation({
    mutationFn: (name: string) =>
      apiJson(`/api/workspace/sources/${name}`, z.unknown(), {
        method: 'DELETE',
        body: JSON.stringify({ workspace_dir: workspaceDir }),
      }),
    onSuccess: () => onRefresh(),
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
          onSubmit={(source) => createSource.mutate(source)}
          isSubmitting={createSource.isPending}
        />
      )}
    </div>
  );
}

function SelectorsPanel({ workspaceDir, selectors, sources, onRefresh }: {
  workspaceDir: string;
  selectors: Selector[];
  sources: Source[];
  onRefresh: () => void;
}) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingSelector, setEditingSelector] = useState<Selector | null>(null);

  const createSelector = useMutation({
    mutationFn: (selector: Partial<Selector>) =>
      apiJson('/api/workspace/selectors', z.unknown(), {
        method: 'POST',
        body: JSON.stringify({ workspace_dir: workspaceDir, ...selector }),
      }),
    onSuccess: () => {
      onRefresh();
      setShowAddModal(false);
    },
  });

  const deleteSelector = useMutation({
    mutationFn: (name: string) =>
      apiJson(`/api/workspace/selectors/${name}`, z.unknown(), {
        method: 'DELETE',
        body: JSON.stringify({ workspace_dir: workspaceDir }),
      }),
    onSuccess: () => onRefresh(),
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

function ProfilesPanel({ workspaceDir, profiles, sources, selectors, onRefresh }: {
  workspaceDir: string;
  profiles: Profile[];
  sources: Source[];
  selectors: Selector[];
  onRefresh: () => void;
}) {
  const [showAddModal, setShowAddModal] = useState(false);

  const deleteProfile = useMutation({
    mutationFn: (name: string) =>
      apiJson(`/api/workspace/profiles/${name}`, z.unknown(), {
        method: 'DELETE',
        body: JSON.stringify({ workspace_dir: workspaceDir }),
      }),
    onSuccess: () => onRefresh(),
  });

  return (
    <div className="config-panel">
      <div className="panel-header">
        <h3>Analysis Profiles</h3>
        <button className="primary-button" onClick={() => setShowAddModal(true)}>
          <Plus size={16} /> Add Profile
        </button>
      </div>

      <div className="config-list">
        {profiles.map((profile) => (
          <div key={profile.name} className="config-item">
            <div className="config-item-header">
              <div className="config-item-title">
                <Settings size={18} />
                <strong>{profile.name}</strong>
              </div>
              <div className="config-item-actions">
                <button onClick={() => deleteProfile.mutate(profile.name)} className="danger">
                  <Trash2 size={14} /> Delete
                </button>
              </div>
            </div>
            <div className="config-item-details">
              {profile.inputs && (
                <div className="detail-row">
                  <span>Inputs:</span>
                  <span>{Object.keys(profile.inputs).join(', ')}</span>
                </div>
              )}
              {profile.analysis && (
                <>
                  <div className="detail-row">
                    <span>LLM Backend:</span>
                    <span>{String((profile.analysis as any).llm_backend || 'none')}</span>
                  </div>
                  <div className="detail-row">
                    <span>Prompt Mode:</span>
                    <span>{String((profile.analysis as any).llm_prompt_mode || 'strict')}</span>
                  </div>
                </>
              )}
            </div>
          </div>
        ))}
      </div>

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Add Profile</h3>
              <button onClick={() => setShowAddModal(false)}>
                <X size={20} />
              </button>
            </div>
            <p>Use the Profiles page for detailed profile creation</p>
            <button onClick={() => setShowAddModal(false)}>Close</button>
          </div>
        </div>
      )}
    </div>
  );
}

function SourceFormModal({
  workspaceDir,
  source,
  onClose,
  onSubmit,
  isSubmitting
}: {
  workspaceDir: string;
  source?: Source;
  onClose: () => void;
  onSubmit: (source: Partial<Source>) => void;
  isSubmitting: boolean;
}) {
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
    onSubmit({
      name: formData.name,
      kind: formData.kind,
      mode: formData.mode,
      connector_type: formData.connector_type,
      enabled: formData.enabled,
      config: formData.config_path ? { path: formData.config_path } : {},
      policies: formData.policies.split(',').map(p => p.trim()).filter(Boolean),
      metadata: { description: `${formData.kind} source` },
    } as any);
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

function SelectorFormModal({
  workspaceDir,
  sources,
  selector,
  onClose,
  onSubmit,
  isSubmitting
}: {
  workspaceDir: string;
  sources: Source[];
  selector?: Selector;
  onClose: () => void;
  onSubmit: (selector: Partial<Selector>) => void;
  isSubmitting: boolean;
}) {
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
